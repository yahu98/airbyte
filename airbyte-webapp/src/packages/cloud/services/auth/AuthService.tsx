import React, { useContext, useEffect, useMemo } from "react";

import { User } from "./types";
import { GoogleAuthService } from "packages/cloud/lib/auth/GoogleAuthService";
import useTypesafeReducer from "components/hooks/useTypesafeReducer";
import {
  actions,
  AuthServiceState,
  authStateReducer,
  initialState,
} from "./reducer";
import { firebaseApp } from "packages/cloud/config/firebase";
import { UserService } from "packages/cloud/lib/domain/users";
import { RequestAuthMiddleware } from "packages/cloud/lib/auth/RequestAuthMiddleware";
import { AuthProviders } from "packages/cloud/lib/auth/AuthProviders";
import { api } from "packages/cloud/config/api";

type Context = {
  user: User | null;
  inited: boolean;
  isLoading: boolean;
  login: (values: { email: string; password: string }) => Promise<User | null>;
  signUp: (form: { email: string; password: string }) => Promise<User | null>;
  logout: () => void;
};

const defaultState: Context = {
  user: null,
  inited: false,
  isLoading: false,
  login: async () => null,
  signUp: async () => null,
  logout: async () => ({}),
};

export const AuthContext = React.createContext<Context>(defaultState);

// TODO: place token into right place
export let token = "";

// TODO: add proper DI service
const authService = new GoogleAuthService();
const userService = new UserService(
  [
    RequestAuthMiddleware({
      getValue(): string {
        return token;
      },
    }),
  ],
  api.cloud
);

export const AuthenticationProvider: React.FC = ({ children }) => {
  const [state, { loggedIn, authInited }] = useTypesafeReducer<
    AuthServiceState,
    typeof actions
  >(authStateReducer, initialState, actions);

  useEffect(() => {
    firebaseApp.auth().onAuthStateChanged(async (currentUser) => {
      if (state.currentUser === null && currentUser) {
        token = await currentUser.getIdToken();

        console.log(currentUser);

        try {
          const user = await userService.getByAuthId(
            currentUser.uid,
            AuthProviders.GoogleIdentityPlatform
          );
          loggedIn(user);
        } catch (err) {
          if (currentUser.email) {
            const user = await userService.create({
              authProvider: AuthProviders.GoogleIdentityPlatform,
              authUserId: currentUser.uid,
              email: currentUser.email,
              name: currentUser.email,
            });
            loggedIn(user);
          }
        }
      } else {
        authInited();
      }
    });
  }, [state.currentUser, loggedIn, authInited]);

  const ctx: Context = useMemo(
    () => ({
      inited: state.inited,
      isLoading: state.loading,
      async login(values: {
        email: string;
        password: string;
      }): Promise<User | null> {
        await authService.login(values.email, values.password);

        return null;
      },
      async logout(): Promise<void> {
        await authService.signOut();
      },
      async signUp(form: {
        email: string;
        password: string;
      }): Promise<User | null> {
        await authService.signUp(form.email, form.password);
        // const user = await userService.create({
        //   authProvider: AuthProviders.GoogleIdentityPlatform,
        //   authUserId: fbUser.user!.uid,
        //   email: form.email,
        //   name: form.email,
        // });

        return null;
      },
      user: state.currentUser,
    }),
    [state]
  );

  return <AuthContext.Provider value={ctx}>{children}</AuthContext.Provider>;
};

export const useAuthService = (): Context => {
  const authService = useContext(AuthContext);
  if (!authService) {
    throw new Error(
      "useAuthService must be used within a AuthenticationService."
    );
  }

  return authService;
};

export const useCurrentUser = (): User => {
  const { user } = useAuthService();
  if (!user) {
    throw new Error("useCurrentUser must be used only within authorised flow");
  }

  return user;
};