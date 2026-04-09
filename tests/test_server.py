"""Service layer tests using FakeZefixClient."""

from mcp_server_zefix.models import (
    Address,
    CompanyRef,
    ZefixAPIError,
    ZefixConnectionError,
    ZefixTimeoutError,
)
from mcp_server_zefix.server import (
    handle_chid_lookup,
    handle_company_structure,
    handle_get_publications,
    handle_list_legal_forms,
    handle_search,
    handle_uid_lookup,
)
from tests.conftest import (
    FakeZefixClient,
    make_company,
    make_legal_form,
    make_shab_publication,
)


class TestHandleSearch:
    async def test_finds_matching_companies(self):
        fake = FakeZefixClient(
            companies=[
                make_company(name="Novartis AG", uid="CHE-100.000.001"),
                make_company(name="Roche AG", uid="CHE-100.000.002"),
            ]
        )
        result = await handle_search(fake, "Novartis")
        assert "Novartis AG" in result
        assert "CHE-100.000.001" in result
        assert "Roche" not in result

    async def test_bare_wildcard_without_filter_returns_message(self):
        fake = FakeZefixClient(
            companies=[make_company(name="Company A")],
        )
        result = await handle_search(fake, "*")
        assert "legal form filter" in result

    async def test_bare_wildcard_with_legal_form_returns_results(self):
        fake = FakeZefixClient(
            companies=[
                make_company(
                    name="Foundation A",
                    legal_form=make_legal_form(id=7, name="Foundation"),
                ),
                make_company(
                    name="Corp B",
                    legal_form=make_legal_form(id=3, name="Corporation"),
                ),
            ]
        )
        result = await handle_search(fake, "*", legal_form_ids=[7])
        assert "Foundation A" in result
        assert "Corp B" not in result

    async def test_wildcard_search(self):
        fake = FakeZefixClient(
            companies=[
                make_company(name="Swiss Pharma AG"),
                make_company(name="Pharma Solutions GmbH"),
                make_company(name="Unrelated Corp"),
            ]
        )
        result = await handle_search(fake, "*pharma*")
        assert "Swiss Pharma AG" in result
        assert "Pharma Solutions GmbH" in result
        assert "Unrelated Corp" not in result

    async def test_filters_by_canton(self):
        fake = FakeZefixClient(
            companies=[
                make_company(name="Zurich AG", canton="ZH"),
                make_company(name="Basel AG", canton="BS"),
            ]
        )
        result = await handle_search(fake, "*AG*", canton="ZH")
        assert "Zurich AG" in result
        assert "Basel AG" not in result

    async def test_filters_by_legal_form(self):
        fake = FakeZefixClient(
            companies=[
                make_company(
                    name="Corp AG",
                    legal_form=make_legal_form(id=3, name="AG"),
                ),
                make_company(
                    name="Small GmbH",
                    legal_form=make_legal_form(id=4, name="GmbH"),
                ),
            ]
        )
        result = await handle_search(fake, "*", legal_form_ids=[3])
        assert "Corp AG" in result
        assert "Small GmbH" not in result

    async def test_filters_inactive_by_default(self):
        fake = FakeZefixClient(
            companies=[
                make_company(name="Active AG", status="ACTIVE"),
                make_company(name="Deleted AG", status="DELETED"),
            ]
        )
        result = await handle_search(fake, "*AG*")
        assert "Active AG" in result
        assert "Deleted AG" not in result

    async def test_includes_inactive_when_requested(self):
        fake = FakeZefixClient(
            companies=[
                make_company(name="Deleted AG", status="DELETED"),
            ]
        )
        result = await handle_search(fake, "*AG*", active_only=False)
        assert "Deleted AG" in result

    async def test_no_results(self):
        fake = FakeZefixClient(companies=[])
        result = await handle_search(fake, "nonexistent")
        assert "No companies found" in result

    async def test_pagination_hint_shown(self):
        companies = [make_company(name=f"Company {i}") for i in range(5)]
        fake = FakeZefixClient(companies=companies)
        result = await handle_search(fake, "Company", max_results=5)
        assert "offset=" in result

    async def test_connection_error_handled(self):
        fake = FakeZefixClient(error=ZefixConnectionError("unreachable"))
        result = await handle_search(fake, "test")
        assert "Could not connect" in result

    async def test_timeout_error_handled(self):
        fake = FakeZefixClient(error=ZefixTimeoutError("slow"))
        result = await handle_search(fake, "test")
        assert "timed out" in result

    async def test_api_error_handled(self):
        fake = FakeZefixClient(error=ZefixAPIError("server error", status_code=500))
        result = await handle_search(fake, "test")
        assert "500" in result


class TestHandleUidLookup:
    async def test_finds_company(self):
        novartis = make_company(name="Novartis AG", uid="CHE-103.867.593")
        fake = FakeZefixClient(companies=[novartis])
        result = await handle_uid_lookup(fake, "CHE-103.867.593")
        assert "# Novartis AG" in result
        assert "CHE-103.867.593" in result

    async def test_finds_company_with_flexible_uid_format(self):
        novartis = make_company(name="Novartis AG", uid="CHE-103.867.593")
        fake = FakeZefixClient(companies=[novartis])
        result = await handle_uid_lookup(fake, "103867593")
        assert "# Novartis AG" in result

    async def test_not_found(self):
        fake = FakeZefixClient(companies=[])
        result = await handle_uid_lookup(fake, "CHE-000.000.000")
        assert "No company found" in result

    async def test_includes_address_in_detail(self):
        company = make_company()
        fake = FakeZefixClient(companies=[company])
        result = await handle_uid_lookup(fake, company.uid)
        assert "Bahnhofstrasse 1" in result

    async def test_includes_capital(self):
        company = make_company(capital=500_000)
        fake = FakeZefixClient(companies=[company])
        result = await handle_uid_lookup(fake, company.uid)
        assert "500,000" in result

    async def test_connection_error_handled(self):
        fake = FakeZefixClient(error=ZefixConnectionError("down"))
        result = await handle_uid_lookup(fake, "CHE-123.456.789")
        assert "Could not connect" in result


class TestHandleChidLookup:
    async def test_finds_company(self):
        company = make_company(name="Test GmbH", chid="CH99999999999")
        fake = FakeZefixClient(companies=[company])
        result = await handle_chid_lookup(fake, "CH99999999999")
        assert "# Test GmbH" in result

    async def test_not_found(self):
        fake = FakeZefixClient(companies=[])
        result = await handle_chid_lookup(fake, "CH00000000000")
        assert "No company found" in result


class TestHandleListLegalForms:
    async def test_lists_forms_sorted_by_id(self):
        fake = FakeZefixClient(
            legal_forms=[
                make_legal_form(id=4, name="GmbH"),
                make_legal_form(id=1, name="Einzelunternehmen"),
                make_legal_form(id=3, name="AG"),
            ]
        )
        result = await handle_list_legal_forms(fake)
        assert "Einzelunternehmen" in result
        assert "AG" in result
        assert "GmbH" in result
        # Verify sorted by ID
        pos_1 = result.index("Einzelunternehmen")
        pos_3 = result.index("AG")
        pos_4 = result.index("GmbH")
        assert pos_1 < pos_3 < pos_4

    async def test_empty_forms(self):
        fake = FakeZefixClient(legal_forms=[])
        result = await handle_list_legal_forms(fake)
        assert "No legal forms" in result

    async def test_connection_error_handled(self):
        fake = FakeZefixClient(error=ZefixConnectionError("down"))
        result = await handle_list_legal_forms(fake)
        assert "Could not connect" in result


class TestHandleGetPublications:
    async def test_returns_timeline(self):
        fake = FakeZefixClient(
            publications=[
                make_shab_publication(
                    date="2026-03-23",
                    message="Capital increased to CHF 111,111.20",
                    mutation_types=("Capital change",),
                ),
                make_shab_publication(
                    date="2025-02-18",
                    message="Board member changed.",
                    mutation_types=("Board/management change",),
                ),
            ]
        )
        result = await handle_get_publications(fake, "CHE-112.158.921")
        assert "2026-03-23" in result
        assert "Capital change" in result
        assert "2025-02-18" in result
        assert "Board/management change" in result

    async def test_no_publications(self):
        fake = FakeZefixClient(publications=[])
        result = await handle_get_publications(fake, "CHE-000.000.000")
        assert "No SHAB publications" in result

    async def test_connection_error_handled(self):
        fake = FakeZefixClient(error=ZefixConnectionError("down"))
        result = await handle_get_publications(fake, "CHE-123.456.789")
        assert "Could not connect" in result


class TestHandleCompanyStructure:
    async def test_parent_shows_full_addresses(self):
        branch_bern = make_company(
            name="Branch Bern",
            uid="CHE-200.000.001",
            address=Address(
                street="Marktgasse 10", zip_code="3011", city="Bern"
            ),
            status="ACTIVE",
        )
        branch_basel = make_company(
            name="Branch Basel",
            uid="CHE-200.000.002",
            address=Address(
                street="Freie Strasse 5", zip_code="4001", city="Basel"
            ),
            status="ACTIVE",
        )
        branches = (
            CompanyRef(
                name="Branch Bern",
                uid="CHE-200.000.001",
                legal_seat="Bern",
                status="ACTIVE",
                ehraid=1001,
            ),
            CompanyRef(
                name="Branch Basel",
                uid="CHE-200.000.002",
                legal_seat="Basel",
                status="ACTIVE",
                ehraid=1002,
            ),
        )
        parent = make_company(
            name="HQ AG",
            uid="CHE-100.000.001",
            branch_offices=branches,
        )
        fake = FakeZefixClient(
            companies=[parent],
            ehraid_map={1001: branch_bern, 1002: branch_basel},
        )
        result = await handle_company_structure(fake, "CHE-100.000.001")
        assert "Company Structure" in result
        assert "HQ AG" in result
        assert "Head office" in result
        assert "Marktgasse 10, 3011 Bern" in result
        assert "Freie Strasse 5, 4001 Basel" in result

    async def test_branch_navigates_to_parent(self):
        branch_detail = make_company(
            name="Branch Bern",
            uid="CHE-200.000.001",
            address=Address(
                street="Marktgasse 10", zip_code="3011", city="Bern"
            ),
            status="ACTIVE",
        )
        branches = (
            CompanyRef(
                name="Branch Bern",
                uid="CHE-200.000.001",
                legal_seat="Bern",
                status="ACTIVE",
                ehraid=1001,
            ),
        )
        parent = make_company(
            name="HQ AG",
            uid="CHE-100.000.001",
            branch_offices=branches,
        )
        branch = make_company(
            name="Branch Bern",
            uid="CHE-200.000.001",
            head_offices=(
                CompanyRef(
                    name="HQ AG",
                    uid="CHE-100.000.001",
                    legal_seat="Zurich",
                    status="ACTIVE",
                ),
            ),
        )
        fake = FakeZefixClient(
            companies=[parent, branch],
            ehraid_map={1001: branch_detail},
        )
        result = await handle_company_structure(fake, "CHE-200.000.001")
        assert "Company Structure" in result
        assert "HQ AG" in result
        assert "Head office" in result
        assert "Marktgasse 10, 3011 Bern" in result

    async def test_fallback_to_seat_without_ehraid(self):
        branches = (
            CompanyRef(
                name="Branch Bern",
                uid="CHE-200.000.001",
                legal_seat="Bern",
                status="ACTIVE",
                ehraid=0,
            ),
        )
        parent = make_company(
            name="HQ AG",
            uid="CHE-100.000.001",
            branch_offices=branches,
        )
        fake = FakeZefixClient(companies=[parent])
        result = await handle_company_structure(fake, "CHE-100.000.001")
        assert "Bern" in result
        assert "Branch Bern" in result

    async def test_no_structure_returns_message(self):
        company = make_company(
            name="Standalone GmbH", uid="CHE-100.000.001"
        )
        fake = FakeZefixClient(companies=[company])
        result = await handle_company_structure(fake, "CHE-100.000.001")
        assert "No parent or branch offices" in result

    async def test_german_structure_labels(self):
        branches = (
            CompanyRef(
                name="Filiale Bern",
                uid="CHE-200.000.001",
                legal_seat="Bern",
                status="ACTIVE",
                ehraid=0,
            ),
        )
        parent = make_company(
            name="HQ AG",
            uid="CHE-100.000.001",
            branch_offices=branches,
            status="ACTIVE",
        )
        fake = FakeZefixClient(companies=[parent])
        result = await handle_company_structure(
            fake, "CHE-100.000.001", language="de"
        )
        assert "Firmenstruktur" in result
        assert "Hauptsitz" in result
        assert "aktiv" in result

    async def test_not_found_returns_message(self):
        fake = FakeZefixClient(companies=[])
        result = await handle_company_structure(fake, "CHE-000.000.000")
        assert "No company found" in result

    async def test_connection_error_handled(self):
        fake = FakeZefixClient(error=ZefixConnectionError("down"))
        result = await handle_company_structure(fake, "CHE-123.456.789")
        assert "Could not connect" in result

    async def test_timeout_error_handled(self):
        fake = FakeZefixClient(error=ZefixTimeoutError("slow"))
        result = await handle_company_structure(fake, "CHE-123.456.789")
        assert "timed out" in result

    async def test_api_error_handled(self):
        fake = FakeZefixClient(
            error=ZefixAPIError("server error", status_code=500)
        )
        result = await handle_company_structure(fake, "CHE-123.456.789")
        assert "500" in result
