package cloud.honeylabs.scarlet;

import android.Manifest;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.SystemClock;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;
import java.util.ArrayList;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@CapacitorPlugin(
    name = "ScarletSpeech",
    permissions = {
        @Permission(strings = { Manifest.permission.RECORD_AUDIO }, alias = "microphone")
    }
)
public class ScarletSpeechPlugin extends Plugin {

    private SpeechRecognizer recognizer;
    private boolean recognitionActive = false;
    private boolean recognizerOnDevice = false;
    private long recognitionStartedAtMs = 0;
    private long lastLevelEventAtMs = 0;

    private TextToSpeech textToSpeech;
    private volatile boolean textToSpeechReady = false;
    private final ConcurrentHashMap<String, Long> utteranceStartedAt = new ConcurrentHashMap<>();

    @Override
    public void load() {
        super.load();
        getActivity().runOnUiThread(this::initializeTextToSpeech);
    }

    @PluginMethod
    public void getCapabilities(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            JSObject result = new JSObject();
            result.put("platform", "android");
            result.put("sdk", Build.VERSION.SDK_INT);
            result.put(
                "recognition_available",
                SpeechRecognizer.isRecognitionAvailable(getContext())
            );
            result.put("on_device_available", isOnDeviceRecognitionAvailable());
            result.put("microphone_permission", getPermissionState("microphone").toString());
            result.put("tts_ready", textToSpeechReady);
            result.put(
                "tts_engine",
                textToSpeech == null ? "" : textToSpeech.getDefaultEngine()
            );
            result.put("tts_max_input_length", TextToSpeech.getMaxSpeechInputLength());
            result.put("locale", "it-IT");
            call.resolve(result);
        });
    }

    @PluginMethod
    public void startListening(PluginCall call) {
        if (getPermissionState("microphone") != PermissionState.GRANTED) {
            requestPermissionForAlias(
                "microphone",
                call,
                "microphonePermissionCallback"
            );
            return;
        }
        beginListening(call);
    }

    @PermissionCallback
    private void microphonePermissionCallback(PluginCall call) {
        if (getPermissionState("microphone") != PermissionState.GRANTED) {
            call.reject("Microphone permission was not granted.", "MICROPHONE_DENIED");
            return;
        }
        beginListening(call);
    }

    private void beginListening(PluginCall call) {
        String localeTag = call.getString("locale", "it-IT");
        boolean preferOnDevice = Boolean.TRUE.equals(
            call.getBoolean("preferOnDevice", true)
        );

        getActivity().runOnUiThread(() -> {
            if (recognitionActive) {
                call.reject("Speech recognition is already active.", "ALREADY_LISTENING");
                return;
            }
            if (!SpeechRecognizer.isRecognitionAvailable(getContext())) {
                call.reject("Speech recognition is not available.", "UNAVAILABLE");
                return;
            }

            boolean useOnDevice = preferOnDevice && isOnDeviceRecognitionAvailable();
            try {
                ensureRecognizer(useOnDevice);
                Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
                );
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, localeTag);
                intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
                intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
                intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, useOnDevice);

                recognitionActive = true;
                recognitionStartedAtMs = SystemClock.elapsedRealtime();
                emitSpeechState("starting", null);
                recognizer.startListening(intent);

                JSObject result = new JSObject();
                result.put("started", true);
                result.put("engine", useOnDevice ? "on_device" : "system_default");
                result.put("locale", localeTag);
                call.resolve(result);
            } catch (Exception error) {
                recognitionActive = false;
                call.reject(
                    "Unable to start speech recognition.",
                    "START_FAILED",
                    error
                );
            }
        });
    }

    @PluginMethod
    public void stopListening(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            if (recognizer != null && recognitionActive) {
                recognizer.stopListening();
                emitSpeechState("stopping", null);
            }
            JSObject result = new JSObject();
            result.put("stopping", recognitionActive);
            call.resolve(result);
        });
    }

    @PluginMethod
    public void cancelListening(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            if (recognizer != null) recognizer.cancel();
            recognitionActive = false;
            emitSpeechState("cancelled", null);
            JSObject result = new JSObject();
            result.put("cancelled", true);
            call.resolve(result);
        });
    }

    @PluginMethod
    public void speak(PluginCall call) {
        String text = call.getString("text", "");
        String localeTag = call.getString("locale", "it-IT");
        boolean flush = Boolean.TRUE.equals(call.getBoolean("flush", false));
        Double rateOption = call.getDouble("rate", 1.0);
        float rate = Math.max(0.5f, Math.min(2.0f, rateOption.floatValue()));

        if (text == null || text.trim().isEmpty()) {
            call.reject("Speech text cannot be empty.", "EMPTY_TEXT");
            return;
        }

        getActivity().runOnUiThread(() -> {
            if (!textToSpeechReady || textToSpeech == null) {
                call.reject("Text to speech is not ready.", "TTS_NOT_READY");
                return;
            }
            Locale locale = Locale.forLanguageTag(localeTag);
            int languageStatus = textToSpeech.setLanguage(locale);
            if (
                languageStatus == TextToSpeech.LANG_MISSING_DATA ||
                languageStatus == TextToSpeech.LANG_NOT_SUPPORTED
            ) {
                call.reject("The requested TTS locale is unavailable.", "LOCALE_UNAVAILABLE");
                return;
            }

            textToSpeech.setSpeechRate(rate);
            String utteranceId = "scarlet-" + UUID.randomUUID();
            utteranceStartedAt.put(utteranceId, SystemClock.elapsedRealtime());
            int result = textToSpeech.speak(
                text,
                flush ? TextToSpeech.QUEUE_FLUSH : TextToSpeech.QUEUE_ADD,
                null,
                utteranceId
            );
            if (result == TextToSpeech.ERROR) {
                utteranceStartedAt.remove(utteranceId);
                call.reject("Text to speech rejected the utterance.", "TTS_FAILED");
                return;
            }

            emitTtsState("queued", utteranceId, null);
            JSObject response = new JSObject();
            response.put("utterance_id", utteranceId);
            response.put("queued", true);
            response.put("text_length", text.length());
            response.put("locale", localeTag);
            response.put("rate", rate);
            call.resolve(response);
        });
    }

    @PluginMethod
    public void stopSpeaking(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            boolean speaking = textToSpeech != null && textToSpeech.isSpeaking();
            if (textToSpeech != null) textToSpeech.stop();
            JSObject response = new JSObject();
            response.put("stopped", speaking);
            call.resolve(response);
        });
    }

    private void initializeTextToSpeech() {
        if (textToSpeech != null) return;
        textToSpeech = new TextToSpeech(getContext(), status -> {
            textToSpeechReady = status == TextToSpeech.SUCCESS;
            if (textToSpeechReady) {
                textToSpeech.setLanguage(Locale.ITALY);
                textToSpeech.setOnUtteranceProgressListener(
                    new UtteranceProgressListener() {
                        @Override
                        public void onStart(String utteranceId) {
                            emitTtsState("started", utteranceId, null);
                        }

                        @Override
                        public void onDone(String utteranceId) {
                            emitTtsState("completed", utteranceId, null);
                            utteranceStartedAt.remove(utteranceId);
                        }

                        @Override
                        @SuppressWarnings("deprecation")
                        public void onError(String utteranceId) {
                            emitTtsState("error", utteranceId, "synthesis_error");
                            utteranceStartedAt.remove(utteranceId);
                        }

                        @Override
                        public void onError(String utteranceId, int errorCode) {
                            emitTtsState(
                                "error",
                                utteranceId,
                                "synthesis_error_" + errorCode
                            );
                            utteranceStartedAt.remove(utteranceId);
                        }

                        @Override
                        public void onStop(String utteranceId, boolean interrupted) {
                            emitTtsState(
                                "stopped",
                                utteranceId,
                                interrupted ? "interrupted" : null
                            );
                            utteranceStartedAt.remove(utteranceId);
                        }
                    }
                );
            }

            JSObject event = new JSObject();
            event.put("phase", textToSpeechReady ? "ready" : "unavailable");
            event.put("elapsed_ms", 0);
            notifyListeners("ttsState", event, true);
        });
    }

    private boolean isOnDeviceRecognitionAvailable() {
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            SpeechRecognizer.isOnDeviceRecognitionAvailable(getContext());
    }

    private void ensureRecognizer(boolean onDevice) {
        if (recognizer != null && recognizerOnDevice == onDevice) return;
        if (recognizer != null) recognizer.destroy();
        if (onDevice) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
                throw new IllegalStateException(
                    "On-device speech recognition requires Android 12 or newer."
                );
            }
            recognizer = SpeechRecognizer.createOnDeviceSpeechRecognizer(getContext());
        } else {
            recognizer = SpeechRecognizer.createSpeechRecognizer(getContext());
        }
        recognizerOnDevice = onDevice;
        recognizer.setRecognitionListener(new ScarletRecognitionListener());
    }

    private void emitSpeechState(String phase, String detail) {
        JSObject event = new JSObject();
        event.put("phase", phase);
        event.put("engine", recognizerOnDevice ? "on_device" : "system_default");
        event.put("elapsed_ms", elapsedSince(recognitionStartedAtMs));
        if (detail != null) event.put("detail", detail);
        notifyListeners("speechState", event);
    }

    private void emitRecognitionResult(String eventName, Bundle results) {
        ArrayList<String> alternatives = results.getStringArrayList(
            SpeechRecognizer.RESULTS_RECOGNITION
        );
        float[] confidences = results.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES);
        JSObject event = new JSObject();
        event.put(
            "text",
            alternatives == null || alternatives.isEmpty() ? "" : alternatives.get(0)
        );
        event.put(
            "alternatives",
            new JSArray(alternatives == null ? new ArrayList<>() : alternatives)
        );
        JSArray confidenceValues = confidences == null
            ? new JSArray()
            : JSArray.from(confidences);
        event.put(
            "confidences",
            confidenceValues == null ? new JSArray() : confidenceValues
        );
        event.put("elapsed_ms", elapsedSince(recognitionStartedAtMs));
        notifyListeners(eventName, event);
    }

    private void emitTtsState(String phase, String utteranceId, String detail) {
        JSObject event = new JSObject();
        event.put("phase", phase);
        event.put("utterance_id", utteranceId == null ? "" : utteranceId);
        Long startedAt = utteranceId == null ? null : utteranceStartedAt.get(utteranceId);
        event.put("elapsed_ms", startedAt == null ? 0 : elapsedSince(startedAt));
        if (detail != null) event.put("detail", detail);
        notifyListeners("ttsState", event);
    }

    private long elapsedSince(long startedAtMs) {
        if (startedAtMs <= 0) return 0;
        return Math.max(0, SystemClock.elapsedRealtime() - startedAtMs);
    }

    private String recognitionErrorName(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_AUDIO:
                return "audio";
            case SpeechRecognizer.ERROR_CLIENT:
                return "client";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
                return "permission";
            case SpeechRecognizer.ERROR_NETWORK:
                return "network";
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:
                return "network_timeout";
            case SpeechRecognizer.ERROR_NO_MATCH:
                return "no_match";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:
                return "busy";
            case SpeechRecognizer.ERROR_SERVER:
                return "server";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                return "speech_timeout";
            case SpeechRecognizer.ERROR_TOO_MANY_REQUESTS:
                return "too_many_requests";
            case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED:
                return "language_not_supported";
            case SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE:
                return "language_unavailable";
            default:
                return "unknown_" + error;
        }
    }

    private class ScarletRecognitionListener implements RecognitionListener {

        @Override
        public void onReadyForSpeech(Bundle params) {
            emitSpeechState("ready", null);
        }

        @Override
        public void onBeginningOfSpeech() {
            emitSpeechState("speech_started", null);
        }

        @Override
        public void onRmsChanged(float rmsdB) {
            long now = SystemClock.elapsedRealtime();
            if (now - lastLevelEventAtMs < 120) return;
            lastLevelEventAtMs = now;
            JSObject event = new JSObject();
            event.put("rms_db", rmsdB);
            event.put("elapsed_ms", elapsedSince(recognitionStartedAtMs));
            notifyListeners("speechLevel", event);
        }

        @Override
        public void onBufferReceived(byte[] buffer) {}

        @Override
        public void onEndOfSpeech() {
            emitSpeechState("speech_ended", null);
        }

        @Override
        public void onError(int error) {
            recognitionActive = false;
            emitSpeechState("error", recognitionErrorName(error));
        }

        @Override
        public void onResults(Bundle results) {
            recognitionActive = false;
            emitRecognitionResult("speechFinal", results);
            emitSpeechState("completed", null);
        }

        @Override
        public void onPartialResults(Bundle partialResults) {
            emitRecognitionResult("speechPartial", partialResults);
        }

        @Override
        public void onEvent(int eventType, Bundle params) {}
    }

    @Override
    protected void handleOnDestroy() {
        super.handleOnDestroy();
        getActivity().runOnUiThread(() -> {
            if (recognizer != null) {
                recognizer.cancel();
                recognizer.destroy();
                recognizer = null;
            }
            if (textToSpeech != null) {
                textToSpeech.stop();
                textToSpeech.shutdown();
                textToSpeech = null;
            }
            recognitionActive = false;
            textToSpeechReady = false;
            utteranceStartedAt.clear();
        });
    }
}
