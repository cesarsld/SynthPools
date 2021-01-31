pragma solidity ^0.6.12;

interface ISynthSwap {
	// Get the address of the Curve pool used to swap a synthetic asset.
	function synth_pools(address _synth) external view returns(address);

	// Get the address of the synthetic asset that _token may be directly swapped for.
	function swappable_synth(address _token) external view returns(address);

	// Return the amount received when performing a cross-asset swap.
	function get_swap_into_synth_amount(address _from, address _synth, uint256 _amount) external view returns(uint256);

	// Return the amount received when swapping out of a settled synth.
	function get_swap_from_synth_amount(address _synth, address _to, uint256 _amount) external view returns(uint256);
	
	// Estimate the final amount received when swapping between _from and _to.
	function get_estimated_swap_amount(address _from, address _to, uint256 _amount) external view returns(uint256);
	
	// Get information about the underlying synth represented by an NFT.
	// owner, synth, time to settle, undderlying balance
	function token_info(uint256 _token_id) external view returns(address, address, uint256, uint256);

	/*
	 * ==mutative==
	 */

	// Perform a cross-asset swap between _from and _synth.
	// if receiver not given, default tto msg.sender
	// if token id not given, is created
	function swap_into_synth(
		address _from,
		address _synth,
		uint256 _amount,
		uint256 _expected,
		address _receiver,
		uint256 _existing_token_id) 
		external payable returns(uint256);

	// Swap the underlying synth represented by an NFT into another asset.
	// receiver defaults to msg.sender if not given
	function swap_from_synth(
		uint256 _token_id,
		address _to,
		uint256 _amount,
		uint256 _expected,
		address _receiver)
		external returns (uint256);

	// Withdraw the underlying synth represented by an NFT.
	// burns nft if amount is balance
	function withdraw(
		uint256 _token_id,
		uint256 _amount,
		address _receiver)
		external returns(uint256);
}