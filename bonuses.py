"""Structured bonus evidence with totals and explanations calculated in Python."""

from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, create_model


class BonusEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence: str = Field(min_length=1, description="Resume evidence, or why absent")


class ItemizedBonus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    _rules: ClassVar[list] = []
    _cap: ClassVar[int] = 0

    def _awards(self):
        for rule in self._rules:
            entry = getattr(self.items, rule["key"])
            if "tiers" in rule:
                rank = entry.rank
                tier = next(
                    (
                        t
                        for t in rule["tiers"]
                        if rank is not None and t["min"] <= rank <= t["max"]
                    ),
                    None,
                )
                points = tier["points"] if tier else 0
                detail = "no qualifying rank" if rank is None else f"rank {rank}"
                if tier:
                    detail += f" ({tier['min']}-{tier['max']} tier); awarded once"
            else:
                points = entry.points
                detail = ""
            yield rule["label"], points, detail, entry.evidence

    @computed_field
    @property
    def total(self) -> int:
        return min(sum(points for _, points, _, _ in self._awards()), self._cap)

    @computed_field
    @property
    def breakdown(self) -> str:
        awards = list(self._awards())
        lines = [
            f"{label}: +{points} points; {detail + '; ' if detail else ''}{evidence}"
            for label, points, detail, evidence in awards
        ]
        subtotal = sum(points for _, points, _, _ in awards)
        lines.append(
            f"Subtotal: {subtotal}; total after {self._cap}-point cap: {self.total}."
        )
        return "\n".join(lines)


def build_bonus_model(role):
    """Require one evidence entry per configured rule; ranked awards cannot stack."""
    fields = {}
    for rule in role.bonus_rules:
        if "tiers" in rule:
            entry = create_model(
                f"{rule['key']}Bonus",
                __base__=BonusEntry,
                rank=(
                    Optional[int],
                    Field(
                        ...,
                        ge=1,
                        description="Best explicitly stated rank for this contest in awards; null if absent. Never use another contest's rank.",
                    ),
                ),
            )
        else:
            entry = create_model(
                f"{rule['key']}Bonus",
                __base__=BonusEntry,
                points=(Literal[tuple([0] + rule["points"])], ...),
            )
        fields[rule["key"]] = (entry, Field(..., description=rule["description"]))
    items = create_model("BonusItems", __config__=ConfigDict(extra="forbid"), **fields)
    bonus = create_model("BonusPoints", __base__=ItemizedBonus, items=(items, ...))
    bonus._rules = role.bonus_rules
    bonus._cap = role.bonus_max
    return bonus
