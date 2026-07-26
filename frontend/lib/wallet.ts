import { createWalletClient, custom, getAddress, type TypedData, type TypedDataDomain } from "viem";
import type { ClientEvmSigner } from "@x402/evm";

const X_LAYER_CHAIN_ID = "0xc4";

interface ProviderError extends Error {
  code?: number;
}

export interface InjectedProvider {
  isOkxWallet?: boolean;
  providers?: InjectedProvider[];
  request<T = unknown>(request: { method: string; params?: readonly unknown[] | object }): Promise<T>;
  on?(event: string, listener: (...args: unknown[]) => void): void;
  removeListener?(event: string, listener: (...args: unknown[]) => void): void;
}

declare global {
  interface Window {
    okxwallet?: InjectedProvider;
    ethereum?: InjectedProvider;
  }
}

export function getOkxProvider(): InjectedProvider | null {
  if (typeof window === "undefined") return null;
  if (window.okxwallet) return window.okxwallet;
  if (window.ethereum?.isOkxWallet) return window.ethereum;
  return window.ethereum?.providers?.find((provider) => provider.isOkxWallet) ?? null;
}

export async function connectedOkxAccount(): Promise<`0x${string}` | null> {
  const provider = getOkxProvider();
  if (!provider) return null;
  const accounts = await provider.request<string[]>({ method: "eth_accounts" });
  return accounts[0] ? getAddress(accounts[0]) : null;
}

export async function connectOkxWallet(): Promise<{
  address: `0x${string}`;
  provider: InjectedProvider;
}> {
  const provider = getOkxProvider();
  if (!provider) {
    throw new Error("OKX Wallet was not found. Install or enable the OKX Wallet browser extension first.");
  }

  const accounts = await provider.request<string[]>({ method: "eth_requestAccounts" });
  if (!accounts[0]) throw new Error("OKX Wallet did not return an account.");

  await ensureXLayer(provider);
  return { address: getAddress(accounts[0]), provider };
}

export async function ensureXLayer(provider: InjectedProvider): Promise<void> {
  const currentChain = await provider.request<string>({ method: "eth_chainId" });
  if (currentChain.toLowerCase() === X_LAYER_CHAIN_ID) return;

  try {
    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: X_LAYER_CHAIN_ID }],
    });
  } catch (caught) {
    const error = caught as ProviderError;
    if (error.code !== 4902) throw caught;
    await provider.request({
      method: "wallet_addEthereumChain",
      params: [
        {
          chainId: X_LAYER_CHAIN_ID,
          chainName: "X Layer Mainnet",
          nativeCurrency: { name: "OKB", symbol: "OKB", decimals: 18 },
          rpcUrls: ["https://rpc.xlayer.tech"],
          blockExplorerUrls: ["https://www.oklink.com/xlayer"],
        },
      ],
    });
  }
}

export function createOkxSigner(
  provider: InjectedProvider,
  address: `0x${string}`
): ClientEvmSigner {
  const walletClient = createWalletClient({
    account: address,
    transport: custom(provider),
  });

  return {
    address,
    async signTypedData({ domain, types, primaryType, message }) {
      return walletClient.signTypedData({
        account: address,
        domain: domain as TypedDataDomain,
        types: types as TypedData,
        primaryType,
        message,
      });
    },
  };
}

export function shortAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export function walletErrorMessage(caught: unknown): string {
  const error = caught as ProviderError;
  if (error?.code === 4001) return "The request was rejected in OKX Wallet. No payment was made.";
  if (error?.code === -32002) return "OKX Wallet already has a pending request. Open the extension to continue.";
  if (error instanceof Error) {
    if (/insufficient/i.test(error.message)) return "The wallet does not have enough USDT0 for this verified run.";
    return error.message;
  }
  return "OKX Wallet could not complete the request.";
}
