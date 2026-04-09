"""Tests for domain models and pure functions."""

from mcp_server_zefix.models import Address, CompanyRef, LegalForm, normalize_uid
from mcp_server_zefix.server import (
    _format_company_detail,
    _format_company_summary,
    _format_structure_table,
)
from tests.conftest import make_company


class TestNormalizeUid:
    def test_with_dots_and_hyphens(self):
        assert normalize_uid("CHE-123.456.789") == "CHE123456789"

    def test_already_clean(self):
        assert normalize_uid("CHE123456789") == "CHE123456789"

    def test_with_spaces(self):
        assert normalize_uid("CHE 123 456 789") == "CHE123456789"

    def test_digits_only_adds_prefix(self):
        assert normalize_uid("123456789") == "CHE123456789"

    def test_lowercase_normalized(self):
        assert normalize_uid("che-123.456.789") == "CHE123456789"

    def test_whitespace_stripped(self):
        assert normalize_uid("  CHE123456789  ") == "CHE123456789"


class TestAddressFormat:
    def test_full_address(self):
        addr = Address(street="Bahnhofstrasse 1", zip_code="8001", city="Zurich")
        assert addr.format() == "Bahnhofstrasse 1, 8001 Zurich"

    def test_empty_address(self):
        assert Address().format() == ""

    def test_city_only(self):
        addr = Address(city="Basel")
        assert addr.format() == "Basel"


class TestValueObjectEquality:
    def test_companies_with_same_data_are_equal(self):
        a = make_company(name="Test AG", uid="CHE-111.222.333")
        b = make_company(name="Test AG", uid="CHE-111.222.333")
        assert a == b

    def test_companies_with_different_uid_are_not_equal(self):
        a = make_company(uid="CHE-111.222.333")
        b = make_company(uid="CHE-999.888.777")
        assert a != b

    def test_legal_form_equality(self):
        assert LegalForm(id=3, name="AG") == LegalForm(id=3, name="AG")
        assert LegalForm(id=3, name="AG") != LegalForm(id=4, name="GmbH")


class TestFormatCompanySummary:
    def test_includes_name_and_uid(self):
        result = _format_company_summary(make_company())
        assert "Example AG" in result
        assert "CHE-123.456.789" in result

    def test_includes_legal_form_and_location(self):
        result = _format_company_summary(make_company())
        assert "Corporation" in result
        assert "Zurich" in result

    def test_minimal_company(self):
        company = make_company(
            name="Minimal GmbH",
            uid="CHE-999.888.777",
            legal_form=None,
            canton="",
            status="",
        )
        result = _format_company_summary(company)
        assert "Minimal GmbH" in result


class TestFormatCompanyDetail:
    def test_full_company(self):
        result = _format_company_detail(make_company())
        assert "# Example AG" in result
        assert "CHE-123.456.789" in result
        assert "Bahnhofstrasse 1" in result
        assert "100,000" in result
        assert "Corporation" in result
        assert "zh.chregister.ch" in result

    def test_empty_purpose_omitted(self):
        company = make_company(purpose="")
        result = _format_company_detail(company)
        assert "Purpose" not in result

    def test_no_capital_omitted(self):
        company = make_company(capital=None)
        result = _format_company_detail(company)
        assert "Capital" not in result

    def test_audit_firms_shown(self):
        company = make_company(
            audit_firms=(
                CompanyRef(name="KPMG AG", uid="CHE-154.017.048", legal_seat="Basel"),
            ),
        )
        result = _format_company_detail(company)
        assert "KPMG AG" in result
        assert "CHE-154.017.048" in result

    def test_old_names_shown(self):
        company = make_company(
            old_names=("Suba Holz AG", "Huber Holzhandel AG"),
        )
        result = _format_company_detail(company)
        assert "Suba Holz AG" in result
        assert "Huber Holzhandel AG" in result

    def test_taken_over_shown(self):
        company = make_company(
            taken_over=(
                CompanyRef(name="Sandoz SA", uid="CHE-102.514.598", legal_seat="Basel"),
            ),
        )
        result = _format_company_detail(company)
        assert "Sandoz SA" in result
        assert "Has taken over" in result

    def test_branch_offices_capped_at_10(self):
        branches = tuple(
            CompanyRef(name=f"Branch {i}", uid=f"CHE-000.000.{i:03d}", legal_seat="X")
            for i in range(15)
        )
        company = make_company(branch_offices=branches)
        result = _format_company_detail(company)
        assert "Branch 0" in result
        assert "Branch 9" in result
        assert "Branch 10" not in result
        assert "5 more" in result

    def test_empty_enrichment_fields_omitted(self):
        company = make_company()
        result = _format_company_detail(company)
        assert "Audit" not in result
        assert "Previous names" not in result
        assert "Absorbed" not in result
        assert "Branch" not in result

    def test_head_offices_shown(self):
        company = make_company(
            head_offices=(
                CompanyRef(
                    name="Parent AG", uid="CHE-100.000.001", legal_seat="Zurich"
                ),
            ),
        )
        result = _format_company_detail(company)
        assert "Head office" in result
        assert "Parent AG" in result
        assert "CHE-100.000.001" in result

    def test_german_labels(self):
        company = make_company(status="ACTIVE")
        result = _format_company_detail(company, language="de")
        assert "aktiv" in result
        assert "Rechtsform" in result
        assert "Sitz" in result
        assert "Adresse" in result
        assert "Zweck" in result


class TestFormatStructureTable:
    def test_table_header_present(self):
        head = make_company(name="HQ AG", uid="CHE-100.000.001")
        result = _format_structure_table(head, (), language="en")
        assert "| # |" in result
        assert "| Role |" in result

    def test_head_office_row_has_full_address(self):
        head = make_company(
            name="HQ AG",
            uid="CHE-100.000.001",
            address=Address(street="Bahnhofstrasse 1", zip_code="8001", city="Zurich"),
        )
        result = _format_structure_table(head, (), language="en")
        assert "Bahnhofstrasse 1, 8001 Zurich" in result
        assert "Head office" in result

    def test_branch_rows_show_seat(self):
        head = make_company(name="HQ AG", uid="CHE-100.000.001")
        branches = (
            CompanyRef(
                name="Branch Bern",
                uid="CHE-200.000.001",
                legal_seat="Bern",
                status="ACTIVE",
            ),
            CompanyRef(
                name="Branch Basel",
                uid="CHE-200.000.002",
                legal_seat="Basel",
                status="ACTIVE",
            ),
        )
        result = _format_structure_table(head, branches, language="en")
        assert "Branch Bern" in result
        assert "Bern" in result
        assert "Branch Basel" in result
        assert "Basel" in result

    def test_capped_notice_shown(self):
        head = make_company(name="HQ AG", uid="CHE-100.000.001")
        branches: list[CompanyRef] = [
            CompanyRef(name=f"Branch {i}", uid=f"CHE-300.000.{i:03d}", legal_seat="X")
            for i in range(3)
        ]
        result = _format_structure_table(
            head, branches, capped=True, language="en"
        )
        assert "Full addresses shown for the first" in result
        assert "registered seat only" in result

    def test_no_capped_notice_when_not_capped(self):
        head = make_company(name="HQ AG", uid="CHE-100.000.001")
        result = _format_structure_table(head, [], capped=False, language="en")
        assert "registered seat only" not in result

    def test_row_count_matches_branches(self):
        head = make_company(name="HQ AG", uid="CHE-100.000.001")
        branches = tuple(
            CompanyRef(name=f"Branch {i}", uid=f"CHE-300.000.{i:03d}", legal_seat="X")
            for i in range(5)
        )
        result = _format_structure_table(head, branches, language="en")
        data_rows = [
            line
            for line in result.split("\n")
            if line.startswith("| ") and line[2].isdigit()
        ]
        assert len(data_rows) == 6

    def test_german_labels(self):
        head = make_company(
            name="HQ AG", uid="CHE-100.000.001", status="ACTIVE"
        )
        branches = [
            CompanyRef(
                name="Filiale Bern",
                uid="CHE-200.000.001",
                legal_seat="Bern",
                status="ACTIVE",
            ),
        ]
        result = _format_structure_table(head, branches, language="de")
        assert "Firmenstruktur" in result
        assert "Hauptsitz" in result
        assert "Zweigniederlassung" in result
        assert "aktiv" in result
        assert "Rolle" in result
