import unittest

import src.detailed_report as detailed_report
from src.detailed_report import fetch_detailed_report, fetch_report_in_blocks, split_date_range


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def fetch_data(self, url, params=None):
        self.calls.append((url, dict(params or {})))
        response = self.responses.pop(0)

        if isinstance(response, Exception):
            raise response

        return response


class RepeatingClient:
    def __init__(self):
        self.calls = []

    def fetch_data(self, url, params=None):
        params = dict(params or {})
        self.calls.append((url, params))

        return [
            {
                "distribuidora": "MA",
                "status": "Concluido",
                "totalTickets": 1,
            }
        ]


class DetailedReportTests(unittest.TestCase):
    def setUp(self):
        detailed_report.REPORT_BLOCK_DELAY_SECONDS = 0
        detailed_report.DETAILED_REPORT_BLOCK_DELAY_SECONDS = 0

    def test_split_date_range_uses_contiguous_inclusive_blocks(self):
        blocks = split_date_range("2026-05-01", "2026-05-27")

        self.assertEqual(
            blocks,
            [
                ("2026-05-01", "2026-05-10"),
                ("2026-05-11", "2026-05-20"),
                ("2026-05-21", "2026-05-27"),
            ],
        )

    def test_fetch_detailed_report_keeps_full_period_success_unchanged(self):
        expected = [{"id": 1, "data": "2026-05-02"}]
        client = FakeClient([expected])

        result = fetch_detailed_report(
            client,
            "https://example.test/detalhado",
            {"dtStart": "2026-05-01", "dtEnd": "2026-05-05"},
        )

        self.assertEqual(result, expected)
        self.assertEqual(len(client.calls), 1)

    def test_fetch_detailed_report_slices_after_failure_and_continues_failed_blocks(self):
        client = FakeClient(
            [
                [
                    {"id": 2, "data": "2026-05-03"},
                    {"id": 1, "data": "2026-05-01"},
                ],
                None,
                [],
                [],
                [
                    {"id": 2, "data": "2026-05-03"},
                    {"id": 3, "data": "2026-05-22"},
                ],
            ]
        )

        result = fetch_detailed_report(
            client,
            "https://example.test/detalhado",
            {"dtStart": "2026-05-01", "dtEnd": "2026-05-27"},
        )

        self.assertEqual(
            result,
            [
                {"id": 1, "data": "2026-05-01"},
                {"id": 2, "data": "2026-05-03"},
                {"id": 3, "data": "2026-05-22"},
            ],
        )
        self.assertEqual(
            [call[1] for call in client.calls],
            [
                {"dtStart": "2026-05-01", "dtEnd": "2026-05-10"},
                {"dtStart": "2026-05-11", "dtEnd": "2026-05-20"},
                {"dtStart": "2026-05-11", "dtEnd": "2026-05-15"},
                {"dtStart": "2026-05-16", "dtEnd": "2026-05-20"},
                {"dtStart": "2026-05-21", "dtEnd": "2026-05-27"},
            ],
        )

    def test_fetch_report_in_blocks_aggregates_summary_totals_into_one_result(self):
        client = FakeClient(
            [
                [
                    {"distribuidora": "MA", "status": "Concluido", "totalTickets": 2},
                    {"distribuidora": "PA", "status": "Aberto", "totalTickets": 1},
                ],
                [
                    {"distribuidora": "MA", "status": "Concluido", "totalTickets": 3},
                    {"distribuidora": "PA", "status": "Aberto", "totalTickets": 4},
                ],
                [
                    {"distribuidora": "MA", "status": "Concluido", "totalTickets": 5},
                ],
            ]
        )

        result = fetch_report_in_blocks(
            client,
            "https://example.test/status-distribuidora",
            {"dtStart": "2026-05-01", "dtEnd": "2026-05-27"},
            identifier="status-distribuidora",
        )

        self.assertEqual(
            result,
            [
                {"distribuidora": "MA", "status": "Concluido", "totalTickets": 10},
                {"distribuidora": "PA", "status": "Aberto", "totalTickets": 5},
            ],
        )

    def test_stress_one_year_custom_range_is_split_and_consolidated(self):
        client = RepeatingClient()

        result = fetch_report_in_blocks(
            client,
            "https://example.test/status-distribuidora",
            {"dtStart": "2025-01-01", "dtEnd": "2025-12-31"},
            identifier="status-distribuidora",
        )

        self.assertEqual(len(client.calls), 37)
        self.assertEqual(
            result,
            [
                {
                    "distribuidora": "MA",
                    "status": "Concluido",
                    "totalTickets": 37,
                }
            ],
        )
        self.assertEqual(client.calls[0][1], {"dtStart": "2025-01-01", "dtEnd": "2025-01-10"})
        self.assertEqual(client.calls[-1][1], {"dtStart": "2025-12-27", "dtEnd": "2025-12-31"})


if __name__ == "__main__":
    unittest.main()
