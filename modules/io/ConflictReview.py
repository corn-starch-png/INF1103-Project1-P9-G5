
# Encapsulate one comparison; repositories retain persistence and the UI displays its result.
class ConflictReview:
    # Keep a stable comparison snapshot without mutating the active household.
    def __init__(self, base, draft, cloud):
        from copy import deepcopy
        self._base, self._draft, self._cloud = deepcopy((base, draft, cloud))

    # Classify one changed field without exposing document IDs.
    @staticmethod
    def _compare(rows, label, field, before, yours, latest):
        if yours == latest:
            return
        reason = "Both changed differently" if yours != before and latest != before else (
            "Changed locally" if yours != before else "Changed in cloud")
        rows.append((label, field.replace("_", " ").capitalize(), before, yours, latest, reason))

    # Match stable identities internally while showing only friendly record names.
    def rows(self):
        rows = []
        self._compare(rows, "Household", "name", self._base["name"], self._draft["name"], self._cloud["name"])
        for section in ("household_members", "fridge", "consumption_history"):
            original, local, remote = [{row["_id"]: row for row in doc[section]} for doc in (self._base, self._draft, self._cloud)]
            ids = dict.fromkeys([*original, *local, *remote])
            for identity in ids:
                before, yours, latest = original.get(identity), local.get(identity), remote.get(identity)
                sample = yours or latest or before
                name = sample.get("Item_Name", sample.get("name", "Record"))
                if sample.get("Unit"):
                    name += f" ({sample['Unit']})"
                label = name
                if yours is None or latest is None:
                    self._compare(rows, label, "record", "Present" if before else "Absent",
                            "Present" if yours else "Absent", "Present" if latest else "Absent")
                for field in dict.fromkeys([*(before or {}), *(yours or {}), *(latest or {})]):
                    if field != "_id":
                        self._compare(rows, label, field, (before or {}).get(field), (yours or {}).get(field), (latest or {}).get(field))
        return rows

    # Keep one row per stable food record, including added and removed batches.
    def food_rows(self, section="fridge"):
        original, local, remote = [{row["_id"]: row for row in doc[section]}
                                   for doc in (self._base, self._draft, self._cloud)]
        rows = []
        for identity in dict.fromkeys([*original, *local, *remote]):
            yours, latest = local.get(identity), remote.get(identity)
            if yours == latest:
                continue
            sample = yours or latest
            name = sample["Item_Name"]
            if section == "consumption_history":
                name += " (" + sample.get("Record_Date", "unknown date") + ")"
            def amount(record):
                if record is None:
                    return "Removed" if identity in original else "-"
                return f"{record['Quantity']:g} {record['Unit']}"
            def expiry(record):
                if section == "consumption_history":
                    return "N/A"
                return record.get("Expiry_Date", "-") if record else "-"
            rows.append((len(rows) + 1, name, amount(yours), amount(latest), expiry(yours), expiry(latest)))
        return rows

    # Size each column to its longest displayed value, with no horizontal dividers.
    @staticmethod
    def _table(headers, rows):
        cells = [[" ".join(str(value).split()) for value in row] for row in [headers, *rows]]
        widths = [max(len(row[index]) for row in cells) for index in range(len(headers))]
        return [" | ".join(value.ljust(width) for value, width in zip(row, widths)) + " |"
                for row in cells]

    # Show only the fridge comparisons
    def render(self):
        lines = ["Fridge Data Differences"]
        headers = ("No.", "Item name", "Your amount", "Cloud amount", "Your expiry", "Cloud expiry")
        rows = self.food_rows("fridge")
        if not rows:
            lines.append("No differences in fridge data.")
            return "\n".join(lines)
        lines.extend(self._table(headers, rows))
        original, local, remote = [{row["_id"]: row for row in doc["fridge"]}
                                   for doc in (self._base, self._draft, self._cloud)]
        number = 0
        for identity in dict.fromkeys([*original, *local, *remote]):
            yours, latest = local.get(identity), remote.get(identity)
            if yours == latest:
                continue
            number += 1
            if yours is None or latest is None:
                continue
            for field in ("Item_Name", "Purchase_Date", "Remarks"):
                if yours.get(field) != latest.get(field):
                    left, right = yours.get(field) or "-", latest.get(field) or "-"
                    lines.append(f"{number}. {field.replace('_', ' ')}: Yours: {left} | Cloud: {right}")
        return "\n".join(lines)
