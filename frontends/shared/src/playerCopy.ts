/** Keep provider diagnostics out of player-facing notifications. */
export function playerError(error:unknown) {
  const value=error as {code?:number;shortMessage?:string;message?:string};
  const message=value?.shortMessage || value?.message || String(error);
  if(value?.code===4001 || /user rejected|user denied|cancelled|canceled/i.test(message)) return 'You cancelled the request. Try again when you’re ready.';
  if(/no browser wallet|provider.*not found/i.test(message)) return 'To sign in, install or unlock a browser wallet, then try again.';
  if(/insufficient funds|exceeds.*balance/i.test(message)) return 'Your account needs a little test credit to publish. Add test funds, then try again.';
  if(/network|fetch|timeout|RPC|HTTP|returned 5\d\d/i.test(message)) return 'We couldn’t reach the service. Check your connection and try again.';
  if(/0x[0-9a-f]{40,}|contract|execution reverted|transaction|gas|ABI/i.test(message)) return 'Your change couldn’t be saved. Refresh the page and try again.';
  return message.length>240?'Your change couldn’t be saved. Please try again.':message;
}
