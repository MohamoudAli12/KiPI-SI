"""A solve of some rails keeps the results of the rails solved before."""

from types import SimpleNamespace

from kipi.dc.pi.results import GroupResult, TreeResult, merge


def tree(*groups, thermal=None):
    """A result with a group, a load and a VRM per (name, nets) in ``groups``."""
    t = TreeResult(thermal=thermal)
    for name, nets in groups:
        t.groups[name] = GroupResult(name, nets, "rail", f"{name} VRM", None)
        t.loads.append(SimpleNamespace(name=f"{name} load", group=name))
        t.vrms.append(SimpleNamespace(name=f"{name} VRM", group=name))
    return t


def test_new_rails_join_the_old_ones_and_resolved_ones_replace_them():
    old = tree(("+3V3", ["+3V3"]), ("+5V", ["+5V", "+5V_F"]), ("GND", ["GND"]))
    new = tree(("+5V", ["+5V"]), ("+1V8", ["+1V8"]), ("GND", ["GND"]))
    out = merge(old, new)
    assert list(out.groups) == ["+3V3", "+5V", "+1V8", "GND"]
    assert out.groups["+5V"] is new.groups["+5V"] and out.groups["GND"] is new.groups["GND"]
    assert [l.name for l in out.loads] == ["+3V3 load", "+5V load", "+1V8 load", "GND load"]
    assert [v.group for v in out.vrms] == ["+3V3", "+5V", "+1V8", "GND"]
    assert list(new.groups) == ["+5V", "+1V8", "GND"]          # new not changed


def test_a_group_sharing_a_net_is_replaced():
    out = merge(tree(("A", ["+5V", "+5V_F"])), tree(("B", ["+5V_F"])))
    assert list(out.groups) == ["B"]


def test_nothing_to_keep_or_thermal_gives_the_new_result():
    new = tree(("+5V", ["+5V"]))
    assert merge(None, new) is new
    assert merge(tree(("+3V3", ["+3V3"]), thermal=object()), new) is new
    assert merge(tree(("+3V3", ["+3V3"])), tree(("+5V", ["+5V"]), thermal=object())).thermal
