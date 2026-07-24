import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "cloud.honeylabs.scarlet",
  appName: "Scarlet",
  webDir: "dist",
  backgroundColor: "#b24592",
  loggingBehavior: "debug",
  android: {
    backgroundColor: "#b24592"
  },
  plugins: {
    CapacitorHttp: {
      enabled: true
    }
  }
};

export default config;
