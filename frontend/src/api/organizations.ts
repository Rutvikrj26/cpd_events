
import client from "./client";

export const getMyInvitations = async () => {
    const response = await client.get("/organizations/invitations/");
    return response.data;
};
