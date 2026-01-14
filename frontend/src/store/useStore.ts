import { create } from "zustand";
import { api, Config, Torrent, Stats } from "../services/api";

export interface ToastNotification {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

interface Store {
  // State
  config: Config | null;
  torrents: Torrent[];
  stats: Stats | null;
  clients: string[];
  ws: WebSocket | null;
  connected: boolean;
  toasts: ToastNotification[];

  // Actions
  setConfig: (config: Config) => void;
  setTorrents: (torrents: Torrent[]) => void;
  setStats: (stats: Stats) => void;
  setClients: (clients: string[]) => void;
  addToast: (message: string, type: "success" | "error" | "info") => void;
  removeToast: (id: string) => void;

  // API calls
  fetchConfig: () => Promise<void>;
  fetchTorrents: () => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchClients: () => Promise<void>;
  updateConfig: (config: Config) => Promise<void>;
  addTorrent: (file: File) => Promise<void>;
  removeTorrent: (infoHash: string) => Promise<void>;
  startSeeding: () => Promise<void>;
  stopSeeding: () => Promise<void>;

  // WebSocket
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
}

export const useStore = create<Store>((set, get) => ({
  // Initial state
  config: null,
  torrents: [],
  stats: null,
  clients: [],
  ws: null,
  connected: false,
  toasts: [],

  // Setters
  setConfig: (config) => set({ config }),
  setTorrents: (torrents) => set({ torrents }),
  setStats: (stats) => set({ stats }),
  setClients: (clients) => set({ clients }),

  addToast: (message, type) => {
    const id = Math.random().toString(36).substring(7);
    set((state) => ({ toasts: [...state.toasts, { id, message, type }] }));
  },

  removeToast: (id) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },

  // Fetch data
  fetchConfig: async () => {
    try {
      const config = await api.getConfig();
      set({ config });
    } catch (error) {
      console.error("Failed to fetch config:", error);
    }
  },

  fetchTorrents: async () => {
    try {
      const torrents = await api.getTorrents();
      set({ torrents });
    } catch (error) {
      console.error("Failed to fetch torrents:", error);
    }
  },

  fetchStats: async () => {
    try {
      const stats = await api.getStats();
      set({ stats });
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    }
  },

  fetchClients: async () => {
    try {
      const clients = await api.getClients();
      set({ clients });
    } catch (error) {
      console.error("Failed to fetch clients:", error);
    }
  },

  updateConfig: async (config) => {
    try {
      await api.updateConfig(config);
      set({ config });
    } catch (error) {
      console.error("Failed to update config:", error);
      throw error;
    }
  },

  addTorrent: async (file) => {
    try {
      const response = await api.addTorrent(file);
      await get().fetchTorrents();
      get().addToast(
        `✅ Torrent added: ${response.data?.name || file.name}`,
        "success"
      );
    } catch (error: any) {
      console.error("Failed to add torrent:", error);
      const errorMsg =
        error.response?.data?.detail || error.message || "Invalid torrent file";
      get().addToast(`❌ Failed to add torrent: ${errorMsg}`, "error");
      throw error;
    }
  },

  removeTorrent: async (infoHash) => {
    try {
      await api.removeTorrent(infoHash);
      await get().fetchTorrents();
    } catch (error) {
      console.error("Failed to remove torrent:", error);
      throw error;
    }
  },

  startSeeding: async () => {
    try {
      await api.start();
      await get().fetchStats();
    } catch (error) {
      console.error("Failed to start seeding:", error);
      throw error;
    }
  },

  stopSeeding: async () => {
    try {
      await api.stop();
      await get().fetchStats();
    } catch (error) {
      console.error("Failed to stop seeding:", error);
      throw error;
    }
  },

  // WebSocket
  connectWebSocket: () => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onopen = () => {
      console.log("WebSocket connected");
      set({ connected: true });
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      set({ connected: false });

      // Reconnect after 3 seconds
      setTimeout(() => {
        if (get().ws === ws) {
          get().connectWebSocket();
        }
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        switch (message.type) {
          case "stats_update":
            set({ stats: message.data });
            break;

          case "torrent_added":
          case "torrent_removed":
            get().fetchTorrents();
            break;

          case "seeding_started":
          case "seeding_stopped":
            get().fetchStats();
            break;
        }
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    set({ ws });
  },

  disconnectWebSocket: () => {
    const { ws } = get();
    if (ws) {
      ws.close();
      set({ ws: null, connected: false });
    }
  },
}));
