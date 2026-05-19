import { adminClient } from "./client";

// Stats
export async function getStatsOverview() { return (await adminClient.get("/stats/overview")).data.data; }
export async function getTokenStats(params?: Record<string,string>) { return (await adminClient.get("/stats/tokens", { params })).data.data; }
export async function getTokenTrend(days=7) { return (await adminClient.get("/stats/tokens/trend", { params: { days } })).data.data; }

// Health
export async function getHealthOverview() { return (await adminClient.get("/health/overview")).data.data; }
export async function getHealthErrors(params?: Record<string,string>) { return (await adminClient.get("/health/errors", { params })).data.data; }
export async function getHealthLoad() { return (await adminClient.get("/health/load")).data.data; }
export async function getOrphanDiscussions() { return (await adminClient.get("/health/orphan-discussions")).data.data; }

// Users
export async function getUsers(params?: Record<string,string>) { return (await adminClient.get("/users", { params })).data.data; }
export async function getUserDetail(id: string) { return (await adminClient.get(`/users/${id}`)).data.data; }
export async function updateUserStatus(id: string, isActive: boolean) { return (await adminClient.put(`/users/${id}/status`, { status: isActive ? "active" : "disabled" })).data.data; }
export async function updateUsername(id: string, username: string) { return (await adminClient.put(`/users/${id}/username`, { username })).data.data; }
export async function resetPassword(id: string, password?: string) { return (await adminClient.put(`/users/${id}/password`, { new_password: password || "Reset123" })).data.data; }
export async function updatePhone(id: string, phone: string) { return (await adminClient.put(`/users/${id}/phone`, { phone })).data.data; }
export async function deleteUser(id: string) { return (await adminClient.delete(`/users/${id}`)).data.data; }
export async function createUser(data: {username:string;password:string;phone?:string}) { return (await adminClient.post("/users", data)).data.data; }

// Discussions
export async function getDiscussions(params?: Record<string,string>) { return (await adminClient.get("/discussions", { params })).data.data; }
export async function getDiscussionDetail(id: string) { return (await adminClient.get(`/discussions/${id}`)).data.data; }
export async function getDiscussionMessages(id: string) { return (await adminClient.get(`/discussions/${id}/messages`)).data.data; }
export async function deleteDiscussion(id: string) { return (await adminClient.delete(`/discussions/${id}`)).data.data; }

// Characters
export async function getCharacters(params?: Record<string,string>) { return (await adminClient.get("/characters", { params })).data.data; }
export async function updateCharacterVisibility(id: string, isPublic: boolean) { return (await adminClient.put(`/characters/${id}/visibility`, { is_public: isPublic })).data.data; }
export async function deleteCharacter(id: string) { return (await adminClient.delete(`/characters/${id}`)).data.data; }

// Gallery
export async function getGallery(params?: Record<string,string>) { return (await adminClient.get("/gallery", { params })).data.data; }
export async function unlistFromGallery(id: string) { return (await adminClient.delete(`/gallery/${id}`)).data.data; }

// Audit
export async function getAuditEvents(params?: Record<string,string>) { return (await adminClient.get("/audit/events", { params })).data.data; }
export async function getAuditEventDetail(id: string) { return (await adminClient.get(`/audit/events/${id}`)).data.data; }
export async function getAuditOperations(params?: Record<string,string>) { return (await adminClient.get("/audit/operations", { params })).data.data; }

// Admins
export async function getAdmins() { return (await adminClient.get("/admins")).data.data; }
export async function createAdmin(data: {username:string;password:string;display_name?:string;role:string}) { return (await adminClient.post("/admins", data)).data.data; }
export async function updateAdmin(id: string, data: Record<string,any>) { return (await adminClient.put(`/admins/${id}`, data)).data.data; }
export async function deleteAdmin(id: string) { return (await adminClient.delete(`/admins/${id}`)).data.data; }

// Settings
export async function getSettings() { return (await adminClient.get("/settings")).data.data; }
export async function updateSettings(data: Record<string,any>) { return (await adminClient.put("/settings", data)).data.data; }
export async function restartService() { return (await adminClient.post("/settings/restart")).data.data; }
export async function updateRetention(data: Record<string,any>) { return (await adminClient.put("/settings/retention", data)).data.data; }

// Auth
import axios from "axios";
const authClient = axios.create({ baseURL: "/api/v1/audit/auth", headers: { "Content-Type": "application/json" }, timeout: 15000 });
export async function loginAudit(username: string, password: string) { return (await authClient.post("/login", { username, password })).data.data; }
