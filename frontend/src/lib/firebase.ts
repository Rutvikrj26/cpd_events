/**
 * Firebase Web SDK wrapper — only used for Google sign-in popup.
 *
 * Initialization is lazy so the app still boots when Firebase env is empty.
 * ``isFirebaseConfigured()`` lets UI hide the "Continue with Google" button
 * until the operator fills in ``VITE_FIREBASE_*``.
 */

import type { FirebaseApp } from "firebase/app";
import { initializeApp } from "firebase/app";
import {
    GoogleAuthProvider,
    getAuth,
    signInWithPopup,
    type Auth,
} from "firebase/auth";

type FirebaseWebConfig = {
    apiKey: string;
    authDomain: string;
    projectId: string;
    appId: string;
};

function readConfig(): FirebaseWebConfig | null {
    const cfg: FirebaseWebConfig = {
        apiKey: import.meta.env.VITE_FIREBASE_API_KEY ?? "",
        authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN ?? "",
        projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID ?? "",
        appId: import.meta.env.VITE_FIREBASE_APP_ID ?? "",
    };
    const missing = Object.entries(cfg).filter(([, v]) => !v);
    if (missing.length > 0) {
        return null;
    }
    return cfg;
}

export function isFirebaseConfigured(): boolean {
    return readConfig() !== null;
}

let _app: FirebaseApp | null = null;
let _auth: Auth | null = null;

function ensureFirebase(): Auth {
    if (_auth) return _auth;
    const cfg = readConfig();
    if (!cfg) {
        throw new Error(
            "Firebase is not configured. Set VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, VITE_FIREBASE_PROJECT_ID, VITE_FIREBASE_APP_ID."
        );
    }
    _app = initializeApp(cfg);
    _auth = getAuth(_app);
    return _auth;
}

/**
 * Run the Google popup flow and return a fresh ID token.
 *
 * Throws if the user cancels, if Firebase isn't configured, or if the popup
 * fails (blocked / offline). The caller should surface the message.
 */
export async function getGoogleIdToken(): Promise<string> {
    const auth = ensureFirebase();
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: "select_account" });
    const result = await signInWithPopup(auth, provider);
    const idToken = await result.user.getIdToken(/* forceRefresh */ true);
    if (!idToken) {
        throw new Error("Google sign-in succeeded but no ID token was returned.");
    }
    return idToken;
}
