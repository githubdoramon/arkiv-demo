type IconName = 'arrow' | 'external' | 'search' | 'close' | 'refresh' | 'back' | 'sign-in' | 'check' | 'alert' | 'pending';
const paths: Record<IconName, string> = {
  check: 'm5 12 4 4L19 6',
  alert: 'M12 7v6m0 4h.01M12 3 2 21h20L12 3Z',
  pending: 'M12 7v5l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0',
  arrow: 'M4 12h15m-6-6 6 6-6 6',
  external: 'M7 17 17 7M7 7h10v10',
  search: 'm16 16 4 4M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0',
  close: 'm6 6 12 12M6 18 18 6',
  refresh: 'M20 7v5h-5M4 17v-5h5M5.4 7a7.5 7.5 0 0 1 12.3-2L20 8M4 16l2.3 3A7.5 7.5 0 0 0 18.6 17',
  back: 'M20 12H5m6-6-6 6 6 6',
  'sign-in': 'M14 4h5v16h-5M3 12h12m-5-5 5 5-5 5',
};
export function Icon({name, className=''}:{name:IconName;className?:string}) {
  return <svg className={'icon '+className} viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]}/></svg>;
}
export function SidequestMark() {
  return <svg className="brand-mark" width="34" height="40" viewBox="0 0 34 40" aria-hidden="true"><path fill="currentColor" d="M13 2h20L20 19H1L13 2Zm1 19h19L21 38H1l13-17Z"/></svg>;
}
export function platformName(value:string) {
  return ({pc:'PC',ps4:'PS4',ps5:'PS5',switch:'Switch','nintendo-switch':'Nintendo Switch','playstation-4':'PlayStation 4','playstation-5':'PlayStation 5','xbox-one':'Xbox One','xbox-series':'Xbox Series X|S','xbox-series-x-s':'Xbox Series X|S'} as Record<string,string>)[value] || value.replaceAll('-',' ');
}
