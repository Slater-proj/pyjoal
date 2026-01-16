import axios from "axios";

const API_BASE = "/api";

// Get SECRET_TOKEN from environment or window (injected by backend)
const getToken = (): string | null => {
  // Check if token is available in window object (injected by backend in index.html)
  if (typeof window !== 'undefined' && (window as any).__PYJOAL_TOKEN__) {
    return (window as any).__PYJOAL_TOKEN__;
  }
  return null;
};

// Configure axios to include token in all requests
axios.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers['X-API-Token'] = token;
  }
  return config;
});

export interface Config {
  minUploadRate: number;
  maxUploadRate: number;
  simultaneousSeed: number;
  client: string;
  keepTorrentWithZeroLeechers: boolean;
  uploadRatioTarget: number;
  seedingDurationLimit: number;
}

export interface Torrent {
  id: string;
  name: string;
  size: number;
  uploaded: number;
  uploadSpeed: number;
  ratio: number;
  seeders: number;
  leechers: number;
  state: string;
  addedAt: string;
  lastAnnounce: string | null;
  nextAnnounce: string | null;
  tracker: string | null;
  seedingTime: number;
}

export interface Stats {
  totalUploaded: number;
  totalRatio: number;
  activeTorrents: number;
  avgUploadSpeed: number;
  isRunning: boolean;
  totalTorrents: number;
  totalDownloaded: number;
  uploadSpeed: number;
  startedAt: string | null;
  uptime: number | null;
}

export interface Version {
  version: string;
}

export const api = {
  // Config
  getConfig: async (): Promise<Config> => {
    const { data } = await axios.get(`${API_BASE}/config`);
    return data;
  },

  updateConfig: async (config: Config) => {
    const { data } = await axios.put(`${API_BASE}/config`, config);
    return data;
  },

  getClients: async (): Promise<string[]> => {
    const { data } = await axios.get(`${API_BASE}/clients`);
    return data.clients;
  },

  // Torrents
  getTorrents: async (): Promise<Torrent[]> => {
    const { data } = await axios.get(`${API_BASE}/torrents`);
    return data;
  },

  addTorrent: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await axios.post(`${API_BASE}/torrents`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  removeTorrent: async (infoHash: string) => {
    const { data } = await axios.delete(`${API_BASE}/torrents/${infoHash}`);
    return data;
  },

  startTorrent: async (infoHash: string) => {
    const { data } = await axios.post(`${API_BASE}/torrents/${infoHash}/start`);
    return data;
  },

  stopTorrent: async (infoHash: string) => {
    const { data } = await axios.post(`${API_BASE}/torrents/${infoHash}/stop`);
    return data;
  },

  // Control
  start: async () => {
    const { data } = await axios.post(`${API_BASE}/start`);
    return data;
  },

  stop: async () => {
    const { data } = await axios.post(`${API_BASE}/stop`);
    return data;
  },

  getStats: async (): Promise<Stats> => {
    const { data } = await axios.get(`${API_BASE}/stats`);
    return data;
  },

  // Version
  getVersion: async (): Promise<Version> => {
    const { data } = await axios.get(`${API_BASE}/version`);
    return data;
  },

  // Alias for backward compatibility - will be assigned after object creation
  uploadTorrent: null as any,
};

// Assign the alias after object creation
api.uploadTorrent = api.addTorrent;

export const fetchConfig = async (): Promise<Config> => {
  return api.getConfig();
};

export const fetchVersion = async (): Promise<Version> => {
  return api.getVersion();
};
