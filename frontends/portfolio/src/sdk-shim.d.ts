declare module '@arkiv-network/sdk' {
  export type PublicArkivClient = any;
  export type WalletArkivClient = any;
  export function createPublicClient(options: any): any;
  export function createWalletClient(options: any): any;
  export const ExpirationTime: { fromDays(days: number): any; atBlock(block: bigint): any };
  export function jsonToPayload(data: object): Uint8Array;
}
declare module '@arkiv-network/sdk/query' { export function eq(name: string, value: unknown): any; }
declare module '@arkiv-network/sdk/chains' { export const localhost: any; export const tiramisu: any; }
