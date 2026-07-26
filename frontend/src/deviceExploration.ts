import { App } from "@capacitor/app";
import { Capacitor, type PluginListenerHandle } from "@capacitor/core";
import { Device } from "@capacitor/device";
import { Geolocation } from "@capacitor/geolocation";
import {
  Haptics,
  NotificationType
} from "@capacitor/haptics";
import {
  LocalNotifications,
  type Importance
} from "@capacitor/local-notifications";
import { Motion, type AccelListenerEvent } from "@capacitor/motion";
import { Network } from "@capacitor/network";

import { appendDeviceObservations } from "./api";
import type { DeviceObservationInput } from "./types";

const OUTBOX_KEY = "scarlet-device-exploration-outbox-v1";
const MOTION_SAMPLE_INTERVAL_MS = 3000;
const FLUSH_DEBOUNCE_MS = 500;

type ExplorerCallbacks = {
  onObservation: (observation: DeviceObservationInput) => void;
  onStatus: (status: string) => void;
};

export class DeviceExplorationController {
  readonly runId = `device_run_${randomId()}`;
  deviceId = "initializing";

  private appState = "unknown";
  private appVersion = "unknown";
  private appBuild = "unknown";
  private handles: PluginListenerHandle[] = [];
  private motionTimer: number | null = null;
  private flushTimer: number | null = null;
  private flushPromise: Promise<void> | null = null;
  private latestAcceleration: AccelListenerEvent | null = null;
  private latestOrientation: {
    alpha: number;
    beta: number;
    gamma: number;
  } | null = null;
  private started = false;

  constructor(private readonly callbacks: ExplorerCallbacks) {}

  async start(): Promise<void> {
    if (this.started) return;
    this.started = true;
    this.callbacks.onStatus("Inizializzo i probe del device");

    const [id, appInfo, state] = await Promise.all([
      Device.getId(),
      App.getInfo(),
      App.getState()
    ]);
    this.deviceId = id.identifier;
    this.appVersion = appInfo.version;
    this.appBuild = appInfo.build;
    this.appState = state.isActive ? "active" : "background";

    await this.registerListeners();
    await this.flush();
    await this.captureSnapshot();
    await this.flush();
    this.callbacks.onStatus("Osservazione attiva");
  }

  async stop(): Promise<void> {
    if (!this.started) return;
    this.started = false;
    if (this.motionTimer !== null) {
      window.clearInterval(this.motionTimer);
      this.motionTimer = null;
    }
    if (this.flushTimer !== null) {
      window.clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }
    await Promise.allSettled(this.handles.map((handle) => handle.remove()));
    this.handles = [];
    await this.flush();
  }

  async captureSnapshot(): Promise<void> {
    await this.capture("device", "snapshot", async () => {
      const [info, languageCode, languageTag] = await Promise.all([
        Device.getInfo(),
        Device.getLanguageCode(),
        Device.getLanguageTag()
      ]);
      return {
        payload: { ...info, languageCode, languageTag },
        normalized: {
          platform: info.platform,
          operating_system: info.operatingSystem,
          os_version: info.osVersion,
          android_sdk: info.androidSDKVersion ?? null,
          model: info.model,
          manufacturer: info.manufacturer,
          virtual: info.isVirtual,
          webview_version: info.webViewVersion,
          memory_used_bytes: info.memUsed ?? null,
          language: languageTag.value
        }
      };
    });

    await this.capture("app", "snapshot", async () => {
      const [info, state, launchUrl] = await Promise.all([
        App.getInfo(),
        App.getState(),
        App.getLaunchUrl()
      ]);
      this.appState = state.isActive ? "active" : "background";
      return {
        payload: { info, state, launchUrl: launchUrl ?? null },
        normalized: {
          app_id: info.id,
          version: info.version,
          build: info.build,
          active: state.isActive,
          launch_url: launchUrl?.url ?? null
        }
      };
    });

    await this.capture("battery", "snapshot", async () => {
      const battery = await Device.getBatteryInfo();
      return {
        payload: battery,
        normalized: {
          level_percent:
            typeof battery.batteryLevel === "number"
              ? Math.round(battery.batteryLevel * 100)
              : null,
          charging: battery.isCharging ?? null
        }
      };
    });

    await this.capture("network", "snapshot", async () => {
      const status = await Network.getStatus();
      return {
        payload: status,
        normalized: {
          connected: status.connected,
          transport: status.connectionType
        }
      };
    });

    await this.capture("location", "permission_snapshot", async () => {
      const permission = await Geolocation.checkPermissions();
      return {
        payload: permission,
        normalized: {
          precise: permission.location,
          approximate: permission.coarseLocation
        }
      };
    });

    await this.capture("notifications", "capability_snapshot", async () => {
      const [permission, channels, pending, delivered] = await Promise.all([
        LocalNotifications.checkPermissions(),
        LocalNotifications.listChannels(),
        LocalNotifications.getPending(),
        LocalNotifications.getDeliveredNotifications()
      ]);
      return {
        payload: { permission, channels, pending, delivered },
        normalized: {
          permission: permission.display,
          channel_count: channels.channels.length,
          pending_count: pending.notifications.length,
          delivered_count: delivered.notifications.length
        }
      };
    });
  }

  async captureLocation(): Promise<void> {
    await this.capture("location", "explicit_position", async () => {
      let permission = await Geolocation.checkPermissions();
      if (
        permission.location !== "granted" &&
        permission.coarseLocation !== "granted"
      ) {
        permission = await Geolocation.requestPermissions({
          permissions: ["location", "coarseLocation"]
        });
      }
      const position = await Geolocation.getCurrentPosition({
        enableHighAccuracy: true,
        timeout: 20000,
        maximumAge: 0
      });
      return {
        payload: { permission, position },
        normalized: {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy_meters: position.coords.accuracy,
          altitude_meters: position.coords.altitude,
          speed_meters_second: position.coords.speed,
          heading_degrees: position.coords.heading,
          precise_permission: permission.location,
          approximate_permission: permission.coarseLocation
        }
      };
    }, true);
  }

  async testNotification(): Promise<void> {
    await this.capture("notifications", "schedule_requested", async () => {
      let permission = await LocalNotifications.checkPermissions();
      if (permission.display !== "granted") {
        permission = await LocalNotifications.requestPermissions();
      }
      if (permission.display !== "granted") {
        throw new Error(`Notification permission is ${permission.display}.`);
      }
      await LocalNotifications.createChannel({
        id: "scarlet-device-lab",
        name: "Scarlet Device Lab",
        description: "Notifiche sperimentali del Device Exploration Layer",
        importance: 3 as Importance,
        vibration: true
      });
      const notificationId = Math.floor(Date.now() % 2_000_000_000);
      const scheduled = await LocalNotifications.schedule({
        notifications: [
          {
            id: notificationId,
            title: "Scarlet · prova device",
            body: "Questa notifica verifica il canale periferico sperimentale.",
            channelId: "scarlet-device-lab",
            schedule: { at: new Date(Date.now() + 2500) },
            extra: {
              source: "device-exploration",
              run_id: this.runId
            }
          }
        ]
      });
      return {
        payload: { permission, scheduled },
        normalized: {
          permission: permission.display,
          notification_id: notificationId,
          delay_ms: 2500
        }
      };
    }, true);
  }

  async testHaptics(): Promise<void> {
    await this.capture("haptics", "success_feedback", async () => {
      await Haptics.notification({ type: NotificationType.Success });
      return {
        payload: { requested_type: NotificationType.Success },
        normalized: { completed: true, effect: "success" }
      };
    }, true);
  }

  async flush(): Promise<void> {
    if (this.flushPromise) return this.flushPromise;
    this.flushPromise = this.performFlush().finally(() => {
      this.flushPromise = null;
    });
    return this.flushPromise;
  }

  private async registerListeners(): Promise<void> {
    this.handles.push(
      await App.addListener("appStateChange", ({ isActive }) => {
        this.appState = isActive ? "active" : "background";
        this.observe("lifecycle", "app_state_change", { isActive }, {
          active: isActive
        });
        if (isActive) void this.flush();
      }),
      await App.addListener("pause", () => {
        this.appState = "paused";
        this.observe("lifecycle", "pause", {}, { active: false });
      }),
      await App.addListener("resume", () => {
        this.appState = "active";
        this.observe("lifecycle", "resume", {}, { active: true });
        void this.flush();
      }),
      await App.addListener("appUrlOpen", (event) => {
        this.observe("lifecycle", "url_open", event, { url: event.url });
      }),
      await Network.addListener("networkStatusChange", (status) => {
        this.observe("network", "status_change", status, {
          connected: status.connected,
          transport: status.connectionType
        });
      }),
      await LocalNotifications.addListener(
        "localNotificationReceived",
        (notification) => {
          this.observe("notifications", "received", notification, {
            notification_id: notification.id,
            title: notification.title
          });
        }
      ),
      await LocalNotifications.addListener(
        "localNotificationActionPerformed",
        (action) => {
          this.observe("notifications", "action_performed", action, {
            notification_id: action.notification.id,
            action_id: action.actionId
          });
        }
      ),
      await Motion.addListener("accel", (event) => {
        this.latestAcceleration = event;
      }),
      await Motion.addListener("orientation", (event) => {
        this.latestOrientation = event;
      })
    );

    this.motionTimer = window.setInterval(() => {
      if (!this.latestAcceleration && !this.latestOrientation) return;
      const acceleration = this.latestAcceleration;
      const orientation = this.latestOrientation;
      this.observe(
        "motion",
        "sample",
        { acceleration, orientation },
        {
          acceleration_magnitude: acceleration
            ? magnitude(acceleration.acceleration)
            : null,
          gravity_magnitude: acceleration
            ? magnitude(acceleration.accelerationIncludingGravity)
            : null,
          rotation_alpha: orientation?.alpha ?? null,
          rotation_beta: orientation?.beta ?? null,
          rotation_gamma: orientation?.gamma ?? null,
          source_interval_ms: acceleration?.interval ?? null,
          sample_interval_ms: MOTION_SAMPLE_INTERVAL_MS
        }
      );
    }, MOTION_SAMPLE_INTERVAL_MS);
  }

  private async capture(
    probe: string,
    eventType: string,
    operation: () => Promise<{
      payload: unknown;
      normalized: unknown;
    }>,
    rethrow = false
  ): Promise<void> {
    try {
      const result = await operation();
      this.observe(probe, eventType, result.payload, result.normalized);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.observe(
        probe,
        `${eventType}_error`,
        { message },
        { available: false, error: message }
      );
      if (rethrow) throw error;
    }
  }

  private observe(
    probe: string,
    eventType: string,
    payload: unknown,
    normalized: unknown
  ): void {
    const observation: DeviceObservationInput = {
      client_event_id: `device_event_${randomId()}`,
      schema_version: "device-observation-v1",
      run_id: this.runId,
      device_id: this.deviceId,
      probe,
      event_type: eventType,
      source: Capacitor.isNativePlatform() ? "capacitor-native" : "capacitor-web",
      app_state: this.appState,
      observed_at: new Date().toISOString(),
      payload: jsonObject(payload),
      normalized: jsonObject(normalized),
      metadata: {
        app_version: this.appVersion,
        app_build: this.appBuild,
        platform: Capacitor.getPlatform(),
        model_context_delivery: false,
        cognitive_persistence: false
      }
    };
    const outbox = readOutbox();
    outbox.push(observation);
    writeOutbox(outbox.slice(-1000));
    this.callbacks.onObservation(observation);
    this.scheduleFlush();
  }

  private scheduleFlush(): void {
    if (this.flushTimer !== null) return;
    this.flushTimer = window.setTimeout(() => {
      this.flushTimer = null;
      void this.flush();
    }, FLUSH_DEBOUNCE_MS);
  }

  private async performFlush(): Promise<void> {
    const pending = readOutbox();
    if (pending.length === 0) return;
    try {
      const batch = pending.slice(0, 100);
      const result = await appendDeviceObservations(batch);
      const sent = new Set(batch.map((item) => item.client_event_id));
      writeOutbox(
        readOutbox().filter((item) => !sent.has(item.client_event_id))
      );
      this.callbacks.onStatus(
        `${result.accepted} osservazioni inviate · ${result.deduplicated} già presenti`
      );
      if (readOutbox().length > 0) {
        this.scheduleFlush();
      }
    } catch (error) {
      this.callbacks.onStatus(
        `Outbox locale: ${readOutbox().length} eventi in attesa`
      );
    }
  }
}

function magnitude(vector: { x: number; y: number; z: number }): number {
  return Number(
    Math.sqrt(vector.x ** 2 + vector.y ** 2 + vector.z ** 2).toFixed(4)
  );
}

function jsonObject(value: unknown): Record<string, unknown> {
  return JSON.parse(JSON.stringify(value ?? {})) as Record<string, unknown>;
}

function randomId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().split("-").join("");
  }
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
}

function readOutbox(): DeviceObservationInput[] {
  try {
    const raw = window.localStorage.getItem(OUTBOX_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as DeviceObservationInput[]) : [];
  } catch {
    return [];
  }
}

function writeOutbox(observations: DeviceObservationInput[]): void {
  try {
    window.localStorage.setItem(OUTBOX_KEY, JSON.stringify(observations));
  } catch {
    // The in-app live view still exposes the observation when storage is full.
  }
}
