import pytest


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture()
def owner(accounts):
    return accounts.at("0x2F0b23f53734252Bda2277357e97e1517d6B042A", force=True)

@pytest.fixture()
def me(accounts):
    return accounts.at("0x742d35cc6634c0532925a3b844bc454e4438f44e", force=True)

@pytest.fixture()
def big(accounts):
    return accounts.at("0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be", force=True)

@pytest.fixture()
def receiver(accounts):
    return accounts[2]

@pytest.fixture()
def fake(interface, owner):
    return interface.IERC20("0xEC0A0915A7c3443862B678B0d4721C7aB133FDCf", owner=owner)

@pytest.fixture()
def wbtc(interface, owner):
    return interface.IERC20("0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", owner=owner)

@pytest.fixture()
def dai(interface, owner):
    return interface.IERC20("0x6b175474e89094c44da98b954eedeac495271d0f", owner=owner)

@pytest.fixture()
def tusd(interface, owner):
    return interface.IERC20("0x0000000000085d4780B73119b644AE5ecd22b376", owner=owner)

@pytest.fixture()
def usdc(interface, owner):
    return interface.IERC20("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", owner=owner)

@pytest.fixture()
def eth():
    return '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'

@pytest.fixture()
def master(SynthPoolMaster,  owner):
    return SynthPoolMaster.deploy({'from': owner})

@pytest.fixture()
def synth_swap(interface):
    return interface.ISynthSwap("0x58A3c68e2D3aAf316239c003779F71aCb870Ee47")