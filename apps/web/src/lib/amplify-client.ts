"use client";

import { Amplify } from "aws-amplify";

let isConfigured = false;

function required(name: string): string {
  const value = process.env[name];
  if (!value || !value.trim()) {
    throw new Error(`Missing ${name}`);
  }
  return value.trim();
}

export function configureAmplify() {
  if (isConfigured) return;

  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: required("NEXT_PUBLIC_COGNITO_USER_POOL_ID"),
        userPoolClientId: required("NEXT_PUBLIC_COGNITO_CLIENT_ID"),
        loginWith: {
          email: true,
        },
      },
    },
  });

  isConfigured = true;
}
