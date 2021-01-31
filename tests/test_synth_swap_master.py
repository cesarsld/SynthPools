import pytest
import brownie
from brownie import Wei

def test_wrong_token(master, fake, dai, big, owner):
    with brownie.reverts("SynthPoolMaster: No swappable synths found."):
        master.createPool(fake, dai, Wei("750000 ether"), {'from':owner})

def test_token(master, synth_swap, wbtc, dai, owner):
    master.createPool(dai, wbtc, Wei("750000 ether"), {'from':owner})
    _from = synth_swap.swappable_synth(wbtc)
    assert master.swapPool(0) == (0, dai, _from, wbtc, 0)

def test_deposit_and_withdraw(master, wbtc, dai, big, me, owner):
    master.createPool(dai, wbtc, Wei("750000 ether"), {'from':owner})
    dai.approve(master, 2 ** 256 - 1, {'from': big})
    dai.approve(master, 2 ** 256 - 1, {'from': me})
    dai.transfer(me, Wei('25000 ether'), {'from':big})
    amount = Wei("75000 ether")
    amount2 = Wei("25000 ether")
    master.depositInPool(0, amount, {'from':big})
    master.depositInPool(0, '25000 ether', {'from':me})
    assert master.poolAmount(0) == Wei('100000 ether')
    assert master.userAmountPerPool(0, me) == Wei('25000 ether')
    assert master.userAmountPerPool(0, big) == Wei('75000 ether')
    master.withdrawFromPool(0, amount2, {'from':me})
    assert master.poolAmount(0) == Wei('75000 ether')
    assert master.userAmountPerPool(0, me) == 0
    master.withdrawFromPool(0, amount2, {'from':big})
    assert master.poolAmount(0) == Wei('50000 ether')
    assert master.userAmountPerPool(0, big) == Wei('50000 ether')
    master.withdrawFromPool(0, amount2 * 2, {'from':big})
    assert master.poolAmount(0) == 0
    assert master.userAmountPerPool(0, big) == 0

def test_non_existent(master, wbtc, dai, big, me, owner):
    # master.createPool(dai, wbtc, Wei("750000 ether"), {'from':owner})
    dai.approve(master, 2 ** 256 - 1, {'from': big})
    amount = Wei("75000 ether")
    with brownie.reverts("SynthPoolMaster: Pool does not exist."):
        master.depositInPool(0, amount, {'from':big})
    with brownie.reverts("SynthPoolMaster: Pool does not exist."):
        master.withdrawFromPool(0, amount, {'from':big})

def test_initiate_revert(master, synth_swap, wbtc, dai, big, me, owner):
    master.createPool(dai, wbtc, Wei("750000 ether"), {'from':owner})
    dai.approve(master, 2 ** 256 - 1, {'from': big})
    amount = Wei("75000 ether")
    master.depositInPool(0, amount, {'from':big})
    (_, _from, synth, to,_) = master.swapPool(0)
    expected = synth_swap.get_swap_into_synth_amount(_from, synth, amount)
    with brownie.reverts("SynthPoolMaster: Pool hasn't reached threshold to execute."):
        master.initiatePoolSwap(0, expected, {'from':owner})


def test_initiate_swap(master, synth_swap, wbtc, dai, big, me, owner):
    master.createPool(dai, wbtc, Wei("750000 ether"), {'from':owner})
    dai.approve(master, 2 ** 256 - 1, {'from': big})
    amount = Wei("750000 ether")
    master.depositInPool(0, amount, {'from':big})
    (_, _from, synth, to,_) = master.swapPool(0)
    expected = synth_swap.get_swap_into_synth_amount(_from, synth, amount)
    master.initiatePoolSwap(0, expected, {'from':owner})
    (_,_,_,_,token) = master.swapPool(0)
    assert token != 0
    with brownie.reverts("SynthPoolMaster: Pool is closed."):
        master.depositInPool(0, amount, {'from':big})
    with brownie.reverts("SynthPoolMaster: Pool is closed."):
        master.withdrawFromPool(0, amount, {'from':big})
    with brownie.reverts("SynthPoolMaster: Swap has not occured yet."):
        master.withdrawAfterSwapFromPool(0)

def test_finalise_swap(master, synth_swap, wbtc, dai, big, me, owner, chain):
    master.createPool(dai, wbtc, Wei("750000 ether"), {'from':owner})
    dai.approve(master, 2 ** 256 - 1, {'from': big})
    amount = Wei("750000 ether")
    master.depositInPool(0, amount, {'from':big})
    (_, _from, synth, to,_) = master.swapPool(0)
    expected = synth_swap.get_swap_into_synth_amount(_from, synth, amount)
    master.initiatePoolSwap(0, expected, {'from':owner})
    (_,_,_,_,token) = master.swapPool(0)
    (_,_,balance,_) = synth_swap.token_info(token)
    chain.sleep(600)
    chain.mine()
    pre = wbtc.balanceOf(master)
    expected = synth_swap.get_swap_from_synth_amount(synth, to, balance) * 99 // 100
    master.finalisePoolSwap(0, expected)
    post = wbtc.balanceOf(master)
    assert post > pre

def test_revert_dep_wit_after_swap(master, synth_swap, wbtc, dai, big, me, owner, chain):
    master.createPool(dai, wbtc, Wei("750000 ether"), {'from':owner})
    dai.approve(master, 2 ** 256 - 1, {'from': big})
    amount = Wei("750000 ether")
    master.depositInPool(0, amount, {'from':big})
    (_, _from, synth, to,_) = master.swapPool(0)
    expected = synth_swap.get_swap_into_synth_amount(_from, synth, amount)
    master.initiatePoolSwap(0, expected, {'from':owner})
    (_,_,_,_,token) = master.swapPool(0)
    (_,_,balance,_) = synth_swap.token_info(token)
    chain.sleep(600)
    chain.mine()
    pre = wbtc.balanceOf(master)
    expected = synth_swap.get_swap_from_synth_amount(synth, to, balance) * 99 // 100
    master.finalisePoolSwap(0, expected)
    post = wbtc.balanceOf(master)
    assert post > pre
    with brownie.reverts("SynthPoolMaster: Pool is closed."):
        master.depositInPool(0, amount, {'from':big})
    with brownie.reverts("SynthPoolMaster: Pool is closed."):
        master.withdrawFromPool(0, amount, {'from':big})

def test_withdraw(master, synth_swap, wbtc, dai, big, me, owner, chain):
    master.createPool(dai, wbtc, Wei("750000 ether"), {'from':owner})
    dai.approve(master, 2 ** 256 - 1, {'from': big})
    amount = Wei("750000 ether")
    master.depositInPool(0, amount, {'from':big})
    (_, _from, synth, to,_) = master.swapPool(0)
    expected = synth_swap.get_swap_into_synth_amount(_from, synth, amount)
    master.initiatePoolSwap(0, expected, {'from':owner})
    (_,_,_,_,token) = master.swapPool(0)
    (_,_,balance,_) = synth_swap.token_info(token)
    chain.sleep(600)
    chain.mine()
    pre = wbtc.balanceOf(master)
    expected = synth_swap.get_swap_from_synth_amount(synth, to, balance) * 99 // 100
    master.finalisePoolSwap(0, expected)
    post = wbtc.balanceOf(master)
    assert post > pre
    prebig = wbtc.balanceOf(big)
    with brownie.reverts("SynthPoolMaster: You did not participate in this swap."):
        master.withdrawAfterSwapFromPool(0, {'from': me})
    master.withdrawAfterSwapFromPool(0, {'from':big})
    assert wbtc.balanceOf(big) - prebig == post - pre
    with brownie.reverts("SynthPoolMaster: Swap has not occured yet."):
        master.withdrawAfterSwapFromPool(0, {'from':big})

def test_withdraw_many(master, synth_swap, wbtc, dai, big, me, owner, chain):
    master.createPool(dai, wbtc, Wei("750000 ether"), {'from':owner})
    dai.approve(master, 2 ** 256 - 1, {'from': big})
    dai.approve(master, 2 ** 256 - 1, {'from': me})
    dai.transfer(me, '250000 ether', {'from':big})
    amount = Wei("750000 ether")
    amount2 = Wei("250000 ether")
    master.depositInPool(0, amount, {'from':big})
    master.depositInPool(0, amount2, {'from':me})
    (_, _from, synth, to,_) = master.swapPool(0)
    expected = synth_swap.get_swap_into_synth_amount(_from, synth, amount)
    master.initiatePoolSwap(0, expected, {'from':owner})
    (_,_,_,_,token) = master.swapPool(0)
    (_,_,balance,_) = synth_swap.token_info(token)
    chain.sleep(600)
    chain.mine()
    pre = wbtc.balanceOf(master)
    expected = synth_swap.get_swap_from_synth_amount(synth, to, balance) * 99 // 100
    master.finalisePoolSwap(0, expected)
    post = wbtc.balanceOf(master)
    assert post > pre
    prebig = wbtc.balanceOf(big)
    with brownie.reverts("SynthPoolMaster: You did not participate in this swap."):
        master.withdrawAfterSwapFromPool(0, {'from': owner})
    master.withdrawAfterSwapFromPool(0, {'from':big})
    assert wbtc.balanceOf(big) - prebig == (post - pre) * 75 // 100
    assert wbtc.balanceOf(master) >=  (post - pre) * 249 // 1000
    with brownie.reverts("SynthPoolMaster: You did not participate in this swap."):
        master.withdrawAfterSwapFromPool(0, {'from':big})
    master.withdrawAfterSwapFromPool(0, {'from':me})
    assert wbtc.balanceOf(master) == 0

def test_withdraw_many_out_ether(master, synth_swap, dai, eth, big, me, owner, chain):
    master.createPool(dai, eth, Wei("750000 ether"), {'from':owner})
    dai.approve(master, 2 ** 256 - 1, {'from': big})
    dai.approve(master, 2 ** 256 - 1, {'from': me})
    dai.transfer(me, '250000 ether', {'from':big})
    amount = Wei("750000 ether")
    amount2 = Wei("250000 ether")
    master.depositInPool(0, amount, {'from':big})
    master.depositInPool(0, amount2, {'from':me})
    (_, _from, synth, to,_) = master.swapPool(0)
    expected = synth_swap.get_swap_into_synth_amount(_from, synth, amount)
    master.initiatePoolSwap(0, expected, {'from':owner})
    (_,_,_,_,token) = master.swapPool(0)
    (_,_,balance,_) = synth_swap.token_info(token)
    chain.sleep(600)
    chain.mine()
    pre = master.balance()
    expected = synth_swap.get_swap_from_synth_amount(synth, to, balance) * 99 // 100
    master.finalisePoolSwap(0, expected)
    post = master.balance()
    assert post > pre
    prebig = big.balance()
    with brownie.reverts("SynthPoolMaster: You did not participate in this swap."):
        master.withdrawAfterSwapFromPool(0, {'from': owner})
    master.withdrawAfterSwapFromPool(0, {'from':big})
    assert big.balance() - prebig == (post - pre) * 75 // 100
    assert master.balance() >=  (post - pre) * 249 // 1000
    with brownie.reverts("SynthPoolMaster: You did not participate in this swap."):
        master.withdrawAfterSwapFromPool(0, {'from':big})
    master.withdrawAfterSwapFromPool(0, {'from':me})
    assert master.balance() == 0

def test_withdraw_many_in_ether(master, synth_swap, wbtc, eth, big, me, owner, chain):
    master.createPool(eth, wbtc, Wei("1500 ether"), {'from':owner})
    amount = Wei("1000 ether")
    amount2 = Wei("650 ether")
    big.transfer(to=me, amount=amount2)
    master.depositInPool(0, amount, {'from':big, 'value':amount})
    master.depositInPool(0, amount2, {'from':me, 'value':amount2})
    (_, _from, synth, to,_) = master.swapPool(0)
    expected = synth_swap.get_swap_into_synth_amount(_from, synth, amount)
    master.initiatePoolSwap(0, expected, {'from':owner})
    (_,_,_,_,token) = master.swapPool(0)
    (_,_,balance,_) = synth_swap.token_info(token)
    chain.sleep(600)
    chain.mine()
    pre = wbtc.balanceOf(master)
    expected = synth_swap.get_swap_from_synth_amount(synth, to, balance) * 99 // 100
    master.finalisePoolSwap(0, expected)
    post = wbtc.balanceOf(master)
    assert post > pre
    prebig = wbtc.balanceOf(big)
    with brownie.reverts("SynthPoolMaster: You did not participate in this swap."):
        master.withdrawAfterSwapFromPool(0, {'from': owner})
    master.withdrawAfterSwapFromPool(0, {'from':big})
    assert wbtc.balanceOf(big) - prebig == (post - pre) * 1000 // 1650
    assert wbtc.balanceOf(master) >=  (post - pre) * 649 // 1650
    with brownie.reverts("SynthPoolMaster: You did not participate in this swap."):
        master.withdrawAfterSwapFromPool(0, {'from':big})
    master.withdrawAfterSwapFromPool(0, {'from':me})
    assert wbtc.balanceOf(master) == 0