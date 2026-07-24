import { existsSync, readdirSync } from "node:fs";
import { homedir, platform } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const isWindows = platform() === "win32";
const javaExecutable = isWindows ? "java.exe" : "java";

function javaMajor(javaHome) {
  if (!javaHome) return null;
  const executable = join(javaHome, "bin", javaExecutable);
  if (!existsSync(executable)) return null;
  const result = spawnSync(executable, ["-version"], { encoding: "utf8" });
  const output = `${result.stdout || ""}${result.stderr || ""}`;
  const match = output.match(/version "(?:1\.)?(\d+)/);
  return match ? Number(match[1]) : null;
}

function localJdkCandidates() {
  const root = join(homedir(), ".jdks");
  if (!existsSync(root)) return [];
  return readdirSync(root)
    .filter((name) => name.startsWith("jdk-21"))
    .map((name) =>
      platform() === "darwin"
        ? join(root, name, "Contents", "Home")
        : join(root, name)
    );
}

const candidates = [
  process.env.JAVA_HOME,
  ...localJdkCandidates(),
  platform() === "darwin"
    ? "/Applications/Android Studio.app/Contents/jbr/Contents/Home"
    : null,
  platform() === "darwin"
    ? "/Applications/Android Studio.app/Contents/jre/Contents/Home"
    : null,
  isWindows && process.env.LOCALAPPDATA
    ? join(
        process.env.LOCALAPPDATA,
        "Programs",
        "Android Studio",
        "jbr"
      )
    : null,
  isWindows
    ? "C:\\Program Files\\Android\\Android Studio\\jbr"
    : null
].filter(Boolean);

const javaHome = candidates.find((candidate) => (javaMajor(candidate) ?? 0) >= 21);
if (!javaHome) {
  throw new Error(
    "Android build requires JDK 21. Set JAVA_HOME to a JDK 21 installation."
  );
}

const androidDirectory = resolve("android");
const wrapper = isWindows ? "gradlew.bat" : "./gradlew";
const result = spawnSync(wrapper, ["clean", "assembleDebug"], {
  cwd: androidDirectory,
  env: { ...process.env, JAVA_HOME: javaHome },
  shell: isWindows,
  stdio: "inherit"
});

process.exit(result.status ?? 1);
