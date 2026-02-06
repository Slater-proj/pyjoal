import { create } from "zustand";
import { api, Config, Torrent, Stats, getToken } from "../services/api";

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
  loadingStatus: string | null;  // null=ready, 'loading_torrents', 'error'

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
  reloadTorrents: () => Promise<void>;
  startSeeding: () => Promise<void>;
  stopSeeding: () => Promise<void>;

  // WebSocket
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  
  // Auto refresh pour réactivité
  startAutoRefresh: () => void;
  stopAutoRefresh: () => void;
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
  loadingStatus: 'loading_torrents',  // Start as loading until backend signals ready

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
      console.log('🔧 Frontend: Updating config:', config);
      console.log('📤 Frontend: Sending config update request...');
      const response = await api.updateConfig(config);
      console.log('✅ Frontend: Config update response:', response);
      
      // Refetch config from server to ensure UI is in sync
      console.log('📥 Frontend: Refetching config from server...');
      const updatedConfig = await api.getConfig();
      console.log('✅ Frontend: Updated config received:', updatedConfig);
      set({ config: updatedConfig });
      console.log('🎯 Frontend: Config state updated successfully');
    } catch (error: any) {
      console.error("❌ Frontend: Failed to update config:", error);
      console.error("❌ Frontend: Full error details:", {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message,
        stack: error.stack
      });
      
      // Extract user-friendly error message
      let userMessage = "Erreur lors de la mise à jour de la configuration";
      
      if (error.response?.data?.detail) {
        // Server returned a specific error message
        userMessage = error.response.data.detail;
      } else if (error.response?.status) {
        // HTTP error codes - translate to user-friendly messages
        switch (error.response.status) {
          case 400:
            userMessage = "Données de configuration invalides";
            break;
          case 401:
            userMessage = "Session expirée, veuillez recharger la page";
            break;
          case 403:
            userMessage = "Accès refusé pour modifier la configuration";
            break;
          case 422:
            userMessage = "Valeurs de configuration incorrectes";
            break;
          case 500:
            userMessage = "Erreur serveur lors de la sauvegarde";
            break;
          case 503:
            userMessage = "Service temporairement indisponible";
            break;
          default:
            userMessage = "Erreur de communication avec le serveur";
        }
      } else if (error.code === 'NETWORK_ERROR' || error.message?.includes('Network')) {
        userMessage = "Problème de connexion réseau";
      } else if (error.message?.includes('timeout')) {
        userMessage = "Délai d'attente dépassé";
      }
      
      console.error("📢 Frontend: User will see message:", userMessage);
      
      // Create simplified error for UI (no HTTP codes or technical details)
      const enhancedError = new Error(userMessage);
      (enhancedError as any).isUserFriendly = true;
      
      throw enhancedError;
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

  reloadTorrents: async () => {
    try {
      const response = await fetch("/api/torrents/reload", {
        method: "POST",
        headers: {
          "X-API-Token": getToken() || "",
        },
      });
      
      if (!response.ok) {
        throw new Error("Failed to reload torrents");
      }
      
      const result = await response.json();
      get().addToast(result.message || "Torrents rechargés", "success");
      
      // Rafraîchir les données
      await get().fetchTorrents();
      await get().fetchStats();
    } catch (error) {
      console.error("Failed to reload torrents:", error);
      get().addToast("Erreur lors du rechargement", "error");
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
        console.log("📡 WebSocket message received:", message.type, message);

        switch (message.type) {
          case "stats_update":
            set({ stats: message.data });
            console.log("📊 Updated stats:", message.data);
            break;

          case "torrents_update":
            // Update torrents list from real-time data
            set({ torrents: message.data.torrents });
            console.log("🔄 Updated torrents:", message.data.torrents.length, "torrents");
            break;

          case "torrent_load_error":
            // Show toast for torrent load error instead of polluting the table
            get().addToast(message.data.message, "error");
            console.log("❌ Torrent load error:", message.data);
            break;

          case "torrent_added":
          case "torrent_removed":
            console.log(`➕/➖ Torrent ${message.type}, refreshing...`);
            get().fetchTorrents();
            break;

          case "seeding_started":
          case "seeding_stopped":
            console.log(`⚡ Seeding ${message.type}, refreshing stats and torrents...`);
            // Update both stats and torrents for comprehensive state
            get().fetchStats();
            get().fetchTorrents();
            break;

          case "loading_status":
            if (message.data?.status === 'ready') {
              set({ loadingStatus: null });
              get().fetchTorrents();
              get().fetchStats();
            } else {
              set({ loadingStatus: message.data?.status || 'loading' });
            }
            break;

          default:
            console.log("❓ Unknown WebSocket message type:", message.type);
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

  // Auto-refresh pour une interface ultra-réactive
  startAutoRefresh: () => {
    // Refresh rapide des stats pour les indicateurs de statut
    const statsInterval = setInterval(() => {
      get().fetchStats();
      get().fetchTorrents();
    }, 3000); // Toutes les 3 secondes

    // Stocker l'interval pour pouvoir l'arrêter
    (get() as any)._refreshInterval = statsInterval;
  },

  stopAutoRefresh: () => {
    const interval = (get() as any)._refreshInterval;
    if (interval) {
      clearInterval(interval);
      (get() as any)._refreshInterval = null;
    }
  },
}));
