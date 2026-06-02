from __future__ import annotations

from dataclasses import dataclass

from src.databases.idatabase import IDatabase


@dataclass
class TableAuditResult:
    """Result of a row count comparison for a single table."""

    table: str
    source_count: int
    target_count: int
    match: bool

    @property
    def discrepancy(self) -> int:
        """Absolute difference between source and target row counts."""
        return abs(self.source_count - self.target_count)


@dataclass
class IntegrityAuditReport:
    """Aggregated audit report comparing row counts across all migrated tables."""

    table_results: list[TableAuditResult]
    all_match: bool

    @property
    def total_source_rows(self) -> int:
        """Sum of row counts across all source tables."""
        return sum(r.source_count for r in self.table_results)

    @property
    def total_target_rows(self) -> int:
        """Sum of row counts across all target tables."""
        return sum(r.target_count for r in self.table_results)

    @property
    def mismatched_tables(self) -> list[TableAuditResult]:
        """List of tables where source and target row counts differ."""
        return [r for r in self.table_results if not r.match]

    def summary(self) -> str:
        """Return a human-readable multi-line audit report."""
        lines: list[str] = ["=== Integrity Audit Report ==="]
        status = "PASS" if self.all_match else "FAIL"
        lines.append(f"Overall: {status}")
        for r in self.table_results:
            icon = "OK" if r.match else "MISMATCH"
            lines.append(
                f"  [{icon}] {r.table}: source={r.source_count:,} target={r.target_count:,}"
            )
        if not self.all_match:
            lines.append(f"  Mismatched tables: {len(self.mismatched_tables)}")
            total_disc = sum(r.discrepancy for r in self.mismatched_tables)
            lines.append(f"  Total discrepancy: {total_disc:,} rows")
        lines.append(
            f"  Total: source={self.total_source_rows:,} target={self.total_target_rows:,}"
        )
        return "\n".join(lines)


async def run_integrity_audit(
    source: IDatabase,
    target: IDatabase,
    table_names: list[str],
) -> IntegrityAuditReport:
    """Run a post-migration integrity audit comparing row counts.

    Performs COUNT on each table in both source and target databases
    and checks for exact 100% row count match.
    """
    results: list[TableAuditResult] = []

    for table in table_names:
        source_count = await source.get_row_count(table)
        target_count = await target.get_row_count(table)
        results.append(
            TableAuditResult(
                table=table,
                source_count=source_count,
                target_count=target_count,
                match=source_count == target_count,
            )
        )

    return IntegrityAuditReport(
        table_results=results,
        all_match=all(r.match for r in results),
    )
