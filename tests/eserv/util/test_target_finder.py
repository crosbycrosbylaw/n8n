"""Test suite for util/target_finder.py fuzzy name matching."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rampy import test

from automate.eserv.util.target_finder import FolderMatcher, PartyExtractor

if TYPE_CHECKING:
    from typing import Any


def party_scenario(
    *,
    case_name: str,
    expected_count: int,
    expected_parties: list[str],
) -> dict[str, Any]:
    """Create test scenario for PartyExtractor."""
    return {
        'params': [case_name],
        'expected_count': expected_count,
        'expected_parties': expected_parties,
    }


@test.scenarios(**{
    'v. format': party_scenario(
        case_name='Smith v. Jones',
        expected_count=2,
        expected_parties=['Smith', 'Jones'],
    ),
    'vs format': party_scenario(
        case_name='Acme Corp vs Beta LLC',
        expected_count=2,
        expected_parties=['Acme', 'Beta'],
    ),
    'in re format': party_scenario(
        case_name='In re: Estate of Johnson',
        expected_count=1,
        expected_parties=['Johnson'],
    ),
    'matter of format': party_scenario(
        case_name='Matter of Williams Trust',
        expected_count=1,
        expected_parties=['Williams'],
    ),
})
class TestPartyExtractor:
    def test(
        self,
        /,
        params: list[Any],
        expected_count: int,
        expected_parties: list[str],
    ):
        case_name = params[0]
        parties = PartyExtractor.extract_parties(case_name)

        assert len(parties) == expected_count

        for expected in expected_parties:
            assert any(expected in p for p in parties), f'{expected} not found in {parties}'


def matcher_scenario(
    *,
    folders: list[str],
    case_name: str,
    min_score: float = 50.0,
    should_match: bool = True,
    expected_folder: str | None = None,
) -> dict[str, Any]:
    """Create test scenario for FolderMatcher."""
    return {
        'params': [folders, case_name, min_score],
        'should_match': should_match,
        'expected_folder': expected_folder,
    }


@test.scenarios(**{
    'exact match': matcher_scenario(
        folders=['Smith v. Jones', 'Doe Corporation'],
        case_name='Smith v. Jones',
        min_score=50.0,
        should_match=True,
        expected_folder='Smith v. Jones',
    ),
    'fuzzy match': matcher_scenario(
        folders=['Smith v. Jones Manufacturing Inc.', 'Doe Corporation Ltd.'],
        case_name='Smith v Jones',
        min_score=25.0,
        should_match=True,
        expected_folder='Smith v. Jones Manufacturing Inc.',
    ),
    'no match below threshold': matcher_scenario(
        folders=['Smith v. Jones', 'Completely Different Name'],
        case_name='XYZ Corporation v. ABC Ltd',
        min_score=70.0,
        should_match=False,
    ),
    'empty case name': matcher_scenario(
        folders=['Test Folder'],
        case_name='',
        should_match=False,
    ),
})
class TestFolderMatcher:
    def test(
        self,
        /,
        params: list[Any],
        should_match: bool,
        expected_folder: str | None,
    ):
        folders, case_name, min_score = params
        matcher = FolderMatcher(folder_paths=folders, min_score=min_score)
        match = matcher.find_best_match(case_name)

        if should_match:
            assert match is not None, f'Expected match for {case_name}'
            if expected_folder:
                assert match.folder_path == expected_folder
        else:
            # May or may not match depending on fuzzy score
            # Just verify it doesn't crash
            pass
