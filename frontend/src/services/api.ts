import axios from "axios";

const API_BASE = "/api";

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
}

export interface Stats {
  isRunning: boolean;
  activeTorrents: number;
  totalTorrents: number;
  totalUploaded: number;
  totalDownloaded: number;
  uploadSpeed: number;
  startedAt: string | null;
  uptime: number | null;
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
};
