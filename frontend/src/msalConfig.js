import { PublicClientApplication } from "@azure/msal-browser";

const AZURE_CLIENT_ID = import.meta.env.VITE_AZURE_CLIENT_ID || "";
const AZURE_TENANT_ID = import.meta.env.VITE_AZURE_TENANT_ID || "common";

export const msalConfig = {
  auth: {
    clientId: AZURE_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${AZURE_TENANT_ID}`,
    redirectUri: window.location.origin,
  },

  cache: {
    cacheLocation: "sessionStorage",
    storeAuthStateInCookie: false,
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);

export const loginRequest = {
  scopes: ["openid", "profile", "email"],
};