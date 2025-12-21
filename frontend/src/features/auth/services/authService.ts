// Auth service - re-exports from api/accounts
export {
    login,
    signup,
    getCurrentUser,
    updateProfile,
    refreshToken,
    verifyEmail,
    resetPassword,
    confirmPasswordReset,
    upgradeToOrganizer,
} from '@/api/accounts';
