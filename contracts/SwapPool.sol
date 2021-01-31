pragma solidity ^0.6.12;
pragma experimental ABIEncoderV2;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "../interfaces/ISynthSwap.sol";

contract SynthPoolMaster is Ownable {
	using SafeERC20 for IERC20;
	using SafeMath for uint256;

	struct SynthSwap {
		uint8	open;
		address from;
		address synth;
		address to;
		uint256 tokenId;
	}

	address constant public ETH_ADD = address(0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE);
	ISynthSwap constant public SYNTH_SWAP = ISynthSwap(0x58A3c68e2D3aAf316239c003779F71aCb870Ee47);

	mapping(uint256 => SynthSwap) public swapPool;

	mapping(uint256 => uint256) public poolThreshold;
	mapping(uint256 => uint256) public poolAmount;
	mapping(uint256 => uint256) public poolReturnAmount;
	mapping(uint256 => mapping (address => uint256)) public userAmountPerPool;
	mapping(address => bool) public authorisedCaller;

	uint256 supply;

	constructor() public {
		authorisedCaller[msg.sender] = true;
	}

	/*
	 * setCaller allows the owner to authorise addresses to create new swap pools
	 */
	function setCaller(address _caller, bool _value) external onlyOwner {
		authorisedCaller[_caller] = _value;
	}

	/*
	 * createPool create a new swap pool that allows to swap assets using the Curve x SNX
	 * cross swap asset protocol.
	 *
	 * _from: input token of the swap (erc20 supported by curve or eth)
	 * _to:  output token of the swap (erc20 supported by curve or eth)
	 * _threshold: minimum amount of token required to execute the swap
	 */
	function createPool(address _from, address _to, uint256 _threshold) external {
		address synth = SYNTH_SWAP.swappable_synth(_to);
		require(authorisedCaller[msg.sender], "SynthPoolMaster: No authorised called.");
		require(synth != address(0) && SYNTH_SWAP.swappable_synth(_from) != address(0),
			"SynthPoolMaster: No swappable synths found.");
		swapPool[supply] = SynthSwap(0, _from, synth, _to, 0);
		poolThreshold[supply] = _threshold;
		supply++;
		if (_from != ETH_ADD)
			IERC20(_from).approve(address(SYNTH_SWAP), uint256(-1));
	}

	/*
	 * depositInPool allows users to deposit their funds in a specific swap pool
	 * expecting their tokens to be swapped to the output token
	 *
	 * _poolId: pool in which tot participate
	 * _amount: amount of tokens sent to the pool
	 * if ether is input token, _amount == msg.value
	 */
	function depositInPool(uint256 _poolId, uint256 _amount) external payable {
		SynthSwap memory swap = swapPool[_poolId];
		require(swap.from != address(0), "SynthPoolMaster: Pool does not exist.");
		require(swap.open == 0, "SynthPoolMaster: Pool is closed.");

		poolAmount[_poolId] = poolAmount[_poolId].add(_amount);
		userAmountPerPool[_poolId][msg.sender] = userAmountPerPool[_poolId][msg.sender].add(_amount);
		if (swap.from == ETH_ADD)
			require(msg.value == _amount, "SynthPoolMaster: Wrong amount sent.");
		else {
			require(msg.value == 0, "SynthPoolMaster: Not expecting ether.");
			IERC20(swap.from).safeTransferFrom(msg.sender, address(this), _amount);
		}
	}

	/*
	 * withdrawFromPool allows users to withdraw their funds from a specific swap pool
	 * if the swap execution hasn't started
	 *
	 * _poolId: pool in which to remove input token from
	 * _amount: amount of tokens remove from the pool
	 */
	function withdrawFromPool(uint256 _poolId, uint256 _amount) external {
		SynthSwap memory swap = swapPool[_poolId];
		require(swap.from != address(0), "SynthPoolMaster: Pool does not exist.");
		require(swap.open == 0, "SynthPoolMaster: Pool is closed.");
		require(userAmountPerPool[_poolId][msg.sender] >= _amount, "SynthPoolMaster: User does not have withdrawable funds.");

		poolAmount[_poolId] = poolAmount[_poolId].sub(_amount);
		userAmountPerPool[_poolId][msg.sender] = userAmountPerPool[_poolId][msg.sender].sub(_amount);
		if (swap.from == ETH_ADD)
			msg.sender.transfer(_amount);
		else
			IERC20(swap.from).safeTransfer(msg.sender, _amount);
	}

	/*
	 * withdrawAfterSwapFromPool allows users to withdraw their output token of a swap
	 * They will receive their share of the swap based on userAmount / totalAmount
	 *
	 * _poolId: pool in which to obtain output token from
	 */
	function withdrawAfterSwapFromPool(uint256 _poolId) external {
		uint256 userAmount = userAmountPerPool[_poolId][msg.sender];
		require(poolReturnAmount[_poolId] > 0, "SynthPoolMaster: Swap has not occured yet.");
		require(userAmount > 0, "SynthPoolMaster: You did not participate in this swap.");

		uint256 output = poolReturnAmount[_poolId].mul(userAmount).div(poolAmount[_poolId]);
		address to = swapPool[_poolId].to;
		delete userAmountPerPool[_poolId][msg.sender];
		poolAmount[_poolId] = poolAmount[_poolId].sub(userAmount);
		poolReturnAmount[_poolId] = poolReturnAmount[_poolId].sub(output);
		if (to == ETH_ADD)
			msg.sender.transfer(output);
		else
			IERC20(to).safeTransfer(msg.sender, output);
	}

	/*
	 * initiatePoolSwap is called by a bot (keeper bot?) to initiate a swap once the pool threshold has been met
	 *
	 * _poolId: pool ID from which to initiate a swap
	 * _expected: minimum amount of synthetic asset expected from the swap
	 */
	function initiatePoolSwap(uint256 _poolId, uint256 _expected) external {
		SynthSwap storage swap = swapPool[_poolId];
		require(poolAmount[_poolId] >= poolThreshold[_poolId], "SynthPoolMaster: Pool hasn't reached threshold to execute.");
		require(swap.open == 0, "SynthPoolMaster: Pool is closed.");

		swap.open = uint8(1);
		if (swap.from == ETH_ADD)
			swap.tokenId = SYNTH_SWAP.swap_into_synth
				{value: poolAmount[_poolId]}
				(swap.from, swap.synth, poolAmount[_poolId], _expected, address(this), 0);
		else
			swap.tokenId = SYNTH_SWAP.swap_into_synth
				(swap.from, swap.synth, poolAmount[_poolId], _expected, address(this), 0);
	}

	/*
	 * finalisePoolSwap is called by a bot (keeper bot?) to finalise a swap
	 *
	 * _poolId: pool ID from which to finalise a swap
	 * _expected: minimum amount of output token expected from the swap
	 */
	function finalisePoolSwap(uint256 _poolId, uint256 _expected) external {
		SynthSwap storage swap = swapPool[_poolId];
		require(swap.open == 1, "SynthPoolMaster: Pool is either finalised or ongoing.");
		(,,uint256 balance, uint256 time) = SYNTH_SWAP.token_info(swap.tokenId);
		require(time == 0, "SynthPoolMaster: Settle time is not over.");
		uint256 pre;
		uint256 post;
		if (swap.to == ETH_ADD)
			pre = address(this).balance;
		else
			pre = IERC20(swap.to).balanceOf(address(this));
		SYNTH_SWAP.swap_from_synth(swap.tokenId, swap.to, balance, _expected, address(this));
		if (swap.to == ETH_ADD)
			post = address(this).balance;
		else
			post = IERC20(swap.to).balanceOf(address(this));
		poolReturnAmount[_poolId] = post.sub(pre);
	}

	function onERC721Received(address operator, address from, uint256 tokenId, bytes calldata data) external returns (bytes4) {
		return SynthPoolMaster.onERC721Received.selector; 
	}

	receive() external payable {}
}