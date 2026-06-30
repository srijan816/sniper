"""Shared Supabase mock helpers for integration tests."""
from __future__ import annotations

from unittest.mock import MagicMock


def make_chainable_table(*, select_data=None, update_data=None):
    """Build a chainable mock matching supabase-py query builder."""
    table = MagicMock()
    chain = MagicMock()
    chain.execute.return_value.data = select_data if select_data is not None else []
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.in_.return_value = chain
    chain.order.return_value = chain
    chain.single.return_value = chain
    table.select.return_value = chain

    if update_data is not None:
        update_chain = MagicMock()
        update_chain.eq.return_value.execute.return_value.data = update_data
        table.update.return_value = update_chain
    else:
        update_chain = MagicMock()
        update_chain.eq.return_value.execute.return_value.data = []
        table.update.return_value = update_chain

    table.insert.return_value.execute.return_value.data = []
    table.delete.return_value.eq.return_value.execute.return_value.data = []
    return table


def make_supabase_db(*, client_id: str, user_id: str, email: str | None = None):
    """Mock Supabase client scoped to one authenticated tenant."""
    db = MagicMock()
    user = MagicMock()
    user.id = user_id
    user.email = email or f"user-{user_id[:8]}@test.com"
    db.auth.get_user.return_value = MagicMock(user=user)

    clients_table = make_chainable_table(select_data=[{"id": client_id, "owner_id": user_id}])
    assets_table = make_chainable_table(select_data=[])
    threats_table = make_chainable_table(select_data=[])
    audit_table = make_chainable_table(select_data=[])

    def table(name: str):
        if name == "clients":
            return clients_table
        if name == "assets":
            return assets_table
        if name == "threats":
            return threats_table
        if name == "audit_logs":
            return audit_table
        return make_chainable_table(select_data=[])

    db.table.side_effect = table
    db._test_assets_table = assets_table
    db._test_threats_table = threats_table
    db._test_clients_table = clients_table
    return db
