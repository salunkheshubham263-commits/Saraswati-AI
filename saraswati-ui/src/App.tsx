import { useState, useEffect, useRef } from "react";
import type { FormEvent } from "react";
import "./App.css";

interface Message {
  sender: "user" | "saraswati";
  text: string;
  intent?: string;
  terminal_output?: string;
  plan?: PlanStep[];
  pendingAction?: PendingEmail;
}

interface PlanStep {
  tool: string;
  intent: string;
  description: string;
  status: string;
}

interface PendingEmail {
  kind: "send_email";
  id: string;
  recipient: string;
  subject: string;
  body: string;
  recipient_name: string;
}

interface SpeechRecognitionAlternativeLike {
  transcript: string;
}

interface SpeechRecognitionEventLike {
  results: ArrayLike<ArrayLike<SpeechRecognitionAlternativeLike>>;
}

interface SpeechRecognitionErrorLike {
  error: string;
}

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorLike) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;
type VoiceRecognitionWindow = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
};

type OrbMode = "idle" | "processing" | "speaking";

interface OrbPoint {
  x: number;
  y: number;
  z: number;
  size: number;
  phase: number;
  speed: number;
  color: string;
}

interface ProjectedPoint {
  x: number;
  y: number;
  z: number;
  size: number;
  color: string;
  alpha: number;
}

interface ApiResponse {
  response?: string;
  detail?: string;
  intent?: string;
  planner?: string;
  terminal_output?: string;
  plan?: PlanStep[];
  pending_action?: PendingEmail;
  audio_base64?: string;
}

/* =========================================================
   SARASWATI MATHEMATICAL ENERGY ORB (WARM ORANGE PALETTE)
   ========================================================= */

function SaraswatiOrb({
  mode,
  pulse,
}: {
  mode: OrbMode;
  pulse: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const modeRef = useRef<OrbMode>(mode);
  const pulseRef = useRef(pulse);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  useEffect(() => {
    pulseRef.current = pulse;
  }, [pulse]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");

    if (!canvas || !ctx) return;

    let width = 0;
    let height = 0;
    let dpr = 1;

    let angle = 0;
    let elapsed = 0;
    let lastFrame = 0;
    let animationFrameId = 0;

    let previousPulse = pulseRef.current;
    let pulseEnergy = 0;

    const pointCount = 230;
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));

    const colors = [
      "#fff6bd",
      "#ffe39a",
      "#ffc052",
      "#ff9a2f",
      "#ff7417",
    ];

    const points: OrbPoint[] = Array.from(
      { length: pointCount },
      (_, i) => {
        const y = 1 - (2 * (i + 0.5)) / pointCount;
        const radialDistance = Math.sqrt(1 - y * y);
        const longitude = goldenAngle * i;

        return {
          x: Math.cos(longitude) * radialDistance,
          y,
          z: Math.sin(longitude) * radialDistance,
          size: 0.55 + Math.random() * 1.15,
          phase: Math.random() * Math.PI * 2,
          speed: 0.5 + Math.random() * 1.7,
          color: colors[Math.floor(Math.random() * colors.length)],
        };
      }
    );

    const connections: Array<[number, number]> = [];

    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const a = points[i];
        const b = points[j];
        const dot = a.x * b.x + a.y * b.y + a.z * b.z;

        if (dot > 0.935) {
          connections.push([i, j]);
        }
      }
    }

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
    resize();

    const render = (timestamp: number) => {
      const delta = lastFrame
        ? Math.min((timestamp - lastFrame) / 16.67, 2)
        : 1;

      lastFrame = timestamp;
      elapsed += delta / 60;
      ctx.clearRect(0, 0, width, height);

      if (width <= 0 || height <= 0) {
        animationFrameId = requestAnimationFrame(render);
        return;
      }

      const currentMode = modeRef.current;
      const processing = currentMode === "processing";
      const speaking = currentMode === "speaking";

      if (pulseRef.current !== previousPulse) {
        previousPulse = pulseRef.current;
        pulseEnergy = 1;
      }

      pulseEnergy *= speaking ? 0.91 : 0.94;
      const animationSpeed = speaking ? 0.032 : processing ? 0.021 : 0.006;
      angle += animationSpeed * delta;

      const breathingSpeed = speaking ? 10 : processing ? 5 : 1.7;
      const breathingAmount = speaking ? 0.045 : processing ? 0.035 : 0.018;
      const breathe =
        1 +
        Math.sin(elapsed * breathingSpeed) * breathingAmount +
        pulseEnergy * (speaking ? 0.12 : 0.035);

      const cx = width / 2;
      const cy = height / 2;
      const radius = Math.min(width, height) * 0.325 * breathe;

      const rotationY = angle;
      const rotationX = Math.sin(elapsed * 0.55) * 0.42;
      const rotationZ = Math.cos(elapsed * 0.31) * 0.18;

      const cosY = Math.cos(rotationY);
      const sinY = Math.sin(rotationY);
      const cosX = Math.cos(rotationX);
      const sinX = Math.sin(rotationX);
      const cosZ = Math.cos(rotationZ);
      const sinZ = Math.sin(rotationZ);

      ctx.save();
      ctx.globalCompositeOperation = "lighter";

      const glow = ctx.createRadialGradient(cx, cy, 1, cx, cy, radius * 1.9);
      glow.addColorStop(
        0,
        speaking ? "rgba(255, 170, 40, 0.24)" : "rgba(255, 135, 24, 0.17)"
      );
      glow.addColorStop(0.35, "rgba(255, 94, 10, 0.10)");
      glow.addColorStop(1, "rgba(255, 65, 0, 0)");

      ctx.fillStyle = glow;
      ctx.fillRect(cx - radius * 1.9, cy - radius * 1.9, radius * 3.8, radius * 3.8);

      for (let i = 0; i < 5; i++) {
        const orbitAngle = angle * (i % 2 === 0 ? 0.7 : -0.48) + i * (Math.PI / 5);
        const orbitPulse =
          1 +
          Math.sin(elapsed * (1.2 + i * 0.4) + i) *
            (speaking ? 0.04 : 0.015) +
          pulseEnergy * 0.035;

        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(orbitAngle);
        ctx.beginPath();
        ctx.ellipse(
          0,
          0,
          radius * (0.64 + i * 0.12) * orbitPulse,
          radius * (0.19 + i * 0.055) * orbitPulse,
          0,
          0,
          Math.PI * 2
        );
        ctx.strokeStyle =
          i % 2 === 0 ? "rgba(255, 184, 65, 0.48)" : "rgba(255, 105, 19, 0.34)";
        ctx.lineWidth = i === 2 ? 1.3 : 0.7;
        ctx.stroke();
        ctx.restore();
      }

      const projected: ProjectedPoint[] = points.map((point) => {
        const x1 = point.x * cosY + point.z * sinY;
        const z1 = -point.x * sinY + point.z * cosY;
        const y2 = point.y * cosX - z1 * sinX;
        const z2 = point.y * sinX + z1 * cosX;
        const x3 = x1 * cosZ - y2 * sinZ;
        const y3 = x1 * sinZ + y2 * cosZ;
        const individualMotion = Math.sin(elapsed * point.speed * 3 + point.phase) * 0.018;
        const zoom =
          1 +
          z2 * 0.19 +
          individualMotion +
          pulseEnergy * (0.025 + Math.max(0, z2) * 0.055);
        const particleRadius = radius * zoom;

        return {
          x: cx + x3 * particleRadius,
          y: cy + y3 * particleRadius,
          z: z2,
          size: point.size * (0.75 + (z2 + 1) * 0.4),
          color: point.color,
          alpha: 0.24 + ((z2 + 1) / 2) * 0.76,
        };
      });

      for (const [first, second] of connections) {
        const a = projected[first];
        const b = projected[second];
        const depth = (a.z + b.z) / 2;

        if (depth < -0.58) continue;

        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = speaking
          ? `rgba(255, 176, 62, ${0.12 + Math.max(0, depth) * 0.24})`
          : `rgba(255, 143, 37, ${0.07 + Math.max(0, depth) * 0.19})`;
        ctx.lineWidth = depth > 0.35 ? 0.85 : 0.5;
        ctx.stroke();
      }

      const rayCount = 64;
      for (let i = 0; i < rayCount; i++) {
        const rayAngle = (i / rayCount) * Math.PI * 2 + angle * (speaking ? 0.24 : 0.12);
        const wave = 0.5 + 0.5 * Math.sin(i * 8.17 + elapsed * 3.5);
        const innerRadius = radius * (0.91 + wave * 0.11);
        const rayLength = radius * (0.11 + wave * 0.30) * (speaking ? 1.18 : 1);
        const outerRadius = innerRadius + rayLength + pulseEnergy * radius * wave * 0.14;

        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(rayAngle) * innerRadius, cy + Math.sin(rayAngle) * innerRadius);
        ctx.lineTo(cx + Math.cos(rayAngle) * outerRadius, cy + Math.sin(rayAngle) * outerRadius);
        ctx.strokeStyle =
          i % 4 === 0
            ? `rgba(255, 224, 128, ${0.25 + wave * 0.55})`
            : `rgba(255, 119, 22, ${0.13 + wave * 0.40})`;
        ctx.lineWidth = i % 5 === 0 ? 1.5 : 0.65;
        ctx.stroke();
      }

      const drawOrder = [...projected].sort((a, b) => a.z - b.z);

      for (const point of drawOrder) {
        const depth = (point.z + 1) / 2;
        const twinkle = 0.72 + 0.28 * Math.sin(elapsed * 4 + point.x * 0.13 + point.y * 0.11);

        ctx.globalAlpha = point.alpha * twinkle;
        ctx.fillStyle = point.color;

        if (depth > 0.6) {
          ctx.shadowBlur = speaking ? 7 : 4;
          ctx.shadowColor = "#ff9b2d";
        } else {
          ctx.shadowBlur = 0;
        }

        ctx.beginPath();
        ctx.arc(point.x, point.y, point.size * (0.75 + depth * 0.55), 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;

      if (speaking || processing) {
        for (let i = 0; i < 3; i++) {
          const waveRadius =
            radius *
            (0.34 + i * 0.12) *
            (1 + 0.035 * Math.sin(elapsed * (speaking ? 7 : 3) + i * 1.8) + pulseEnergy * 0.07);

          ctx.beginPath();
          ctx.arc(cx, cy, waveRadius, angle * (i % 2 === 0 ? 1 : -1), angle * (i % 2 === 0 ? 1 : -1) + Math.PI * (1.12 + i * 0.2));
          ctx.strokeStyle = speaking
            ? `rgba(255, 207, 99, ${0.35 - i * 0.065})`
            : `rgba(255, 144, 37, ${0.25 - i * 0.04})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      const coreSize =
        (speaking ? 5.7 : processing ? 5 : 4.2) *
        (1 + Math.sin(elapsed * (speaking ? 8 : 2)) * (speaking ? 0.20 : 0.07) + pulseEnergy * 0.8);

      const coreGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius * 0.38);
      coreGlow.addColorStop(0, "rgba(255,255,226,1)");
      coreGlow.addColorStop(0.09, "rgba(255,236,154,0.98)");
      coreGlow.addColorStop(0.24, "rgba(255,166,39,0.65)");
      coreGlow.addColorStop(0.56, "rgba(255,100,16,0.20)");
      coreGlow.addColorStop(1, "rgba(255,65,0,0)");

      ctx.fillStyle = coreGlow;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 0.38, 0, Math.PI * 2);
      ctx.fill();

      ctx.shadowBlur = speaking ? 24 + pulseEnergy * 18 : 15;
      ctx.shadowColor = speaking ? "#ffcc66" : "#ff982b";
      ctx.fillStyle = "#fff8cd";
      ctx.beginPath();
      ctx.arc(cx, cy, coreSize, 0, Math.PI * 2);
      ctx.fill();

      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
      ctx.restore();

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);
    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden="true" className="block h-full w-full" />;
}

/* =========================================================
   MAIN SARASWATI APPLICATION
   ========================================================= */

function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: "saraswati",
      text: "Saraswati protocol active. How may I help you, Sir?",
    },
  ]);

  const [loading, setLoading] = useState(false);
  const isVoiceEnabled = true;
  const [plannerMode, setPlannerMode] = useState("LOCAL MODEL: CONNECTING");
  const [orbMode, setOrbMode] = useState<OrbMode>("idle");
  const [orbPulse] = useState(0);
  const [isListening, setIsListening] = useState(false);
  const [voiceInputError, setVoiceInputError] = useState("");
  const [confirmingActionId, setConfirmingActionId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, loading]);

  useEffect(() => {
    const audio = new Audio();
    audioRef.current = audio;
    audio.onended = () => setOrbMode("idle");
    audio.onerror = () => setOrbMode("idle");

    return () => {
      audio.pause();
      audio.src = "";
      audioRef.current = null;
    };
  }, []);

  useEffect(
    () => () => {
      recognitionRef.current?.stop();
    },
    []
  );

  /* =======================================================
     PLAY BACKEND DOWNLOADED AUDIO (KOKORO NEURAL VOICE)
     ======================================================= */

  const playAudioBase64 = (base64Audio?: string) => {
    const audio = audioRef.current;
    if (!isVoiceEnabled || !base64Audio || !audio) return;
    setOrbMode("speaking");
    audio.pause();
    audio.src = `data:audio/wav;base64,${base64Audio}`;
    audio.currentTime = 0;
    void audio.play().catch(() => setOrbMode("idle"));
  };

  const speakText = async (text: string) => {
    if (!isVoiceEnabled) return;
    setOrbMode("speaking");
    try {
      const response = await fetch("http://127.0.0.1:8000/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) {
        throw new Error(`Speech request failed: ${response.status}`);
      }
      const data: ApiResponse = await response.json();
      if (data.audio_base64) {
        playAudioBase64(data.audio_base64);
      } else {
        setOrbMode("idle");
      }
    } catch (error) {
      console.error("Unable to play Saraswati speech.", error);
      setOrbMode("idle");
    }
  };

  const updatePendingEmail = (
    actionId: string,
    field: "recipient" | "subject" | "body",
    value: string
  ) => {
    setMessages((previous) =>
      previous.map((message) =>
        message.pendingAction?.id === actionId
          ? {
              ...message,
              pendingAction: {
                ...message.pendingAction,
                [field]: value,
              },
            }
          : message
      )
    );
  };

  const sendConfirmedEmail = async (
    messageIndex: number,
    pendingAction: PendingEmail
  ) => {
    setConfirmingActionId(pendingAction.id);
    let draftCanBeRetried = false;
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/confirm/${pendingAction.id}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            recipient: pendingAction.recipient,
            subject: pendingAction.subject,
            body: pendingAction.body,
          }),
        }
      );
      draftCanBeRetried = response.status === 422;
      const data: ApiResponse = await response.json();
      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `Email confirmation failed: ${response.status}`
        );
      }
      setMessages((previous) =>
        previous.map((message, index) =>
          index === messageIndex
            ? {
                ...message,
                text: data.response ?? "Email sent.",
                pendingAction: undefined,
              }
            : message
        )
      );
      if (isVoiceEnabled && data.audio_base64) {
        playAudioBase64(data.audio_base64);
      }
    } catch (error) {
      const text =
        error instanceof Error ? error.message : "Unable to send the email.";
      setMessages((previous) =>
        previous.map((message, index) =>
          index === messageIndex
            ? {
                ...message,
                text,
                pendingAction: draftCanBeRetried
                  ? message.pendingAction
                  : undefined,
              }
            : message
        )
      );
      setOrbMode("idle");
    } finally {
      setConfirmingActionId(null);
    }
  };

  const cancelPendingEmail = async (
    messageIndex: number,
    pendingAction: PendingEmail
  ) => {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/confirm/${pendingAction.id}`,
        { method: "DELETE" }
      );
      if (!response.ok) {
        throw new Error(`Unable to cancel email draft: ${response.status}`);
      }
      setMessages((previous) =>
        previous.map((message, index) =>
          index === messageIndex
            ? {
                ...message,
                text: "Email draft cancelled.",
                pendingAction: undefined,
              }
            : message
        )
      );
    } catch (error) {
      console.error("Unable to cancel email draft.", error);
    }
  };

  const executeQuery = async (query: string, retainInputWhileRunning = false) => {
    const userQuery = query.trim();
    if (!userQuery || loading) return;

    if (!retainInputWhileRunning) {
      setInput("");
    }
    setMessages((previous) => [
      ...previous,
      {
        sender: "user",
        text: userQuery,
      },
    ]);
    setLoading(true);
    setOrbMode("processing");

    try {
      const response = await fetch("http://127.0.0.1:8000/api/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: userQuery,
        }),
      });

      const data: ApiResponse = await response.json();
      if (!response.ok) {
        throw new Error(
          data.detail ?? `Backend request failed: ${response.status}`
        );
      }
      const responseText =
        typeof data.response === "string" && data.response.trim()
          ? data.response
          : "Task executed successfully, Sir.";
      setPlannerMode(
        data.planner === "ollama"
          ? "LOCAL MODEL: OLLAMA"
          : "LOCAL MODEL: FALLBACK"
      );

      setMessages((previous) => [
        ...previous,
        {
          sender: "saraswati",
          text: responseText,
          intent: data.intent,
          terminal_output: data.terminal_output,
          plan: data.plan,
          pendingAction: data.pending_action,
        },
      ]);

      if (isVoiceEnabled && data.audio_base64) {
        playAudioBase64(data.audio_base64);
      } else {
        setOrbMode("idle");
      }
    } catch (error) {
      setPlannerMode("LOCAL MODEL: FALLBACK");
      const errorText =
        error instanceof Error
          ? error.message
          : "Error connecting to Saraswati backend system.";
      setMessages((previous) => [
        ...previous,
        {
          sender: "saraswati",
          text: errorText,
        },
      ]);
      setOrbMode("idle");
    } finally {
      if (retainInputWhileRunning) {
        setInput("");
      }
      setLoading(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void executeQuery(input);
  };

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const recognitionWindow = window as VoiceRecognitionWindow;
    const Recognition =
      recognitionWindow.SpeechRecognition ??
      recognitionWindow.webkitSpeechRecognition;
    if (!Recognition) {
      setVoiceInputError("Voice input is not supported in this browser.");
      return;
    }

    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript.trim();
      if (transcript) {
        setInput(transcript);
        void executeQuery(transcript, true);
      }
    };
    recognition.onerror = (event) => {
      setVoiceInputError(`Voice input failed: ${event.error}.`);
      setOrbMode("idle");
    };
    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
      setOrbMode((mode) => (mode === "processing" ? mode : "idle"));
    };

    setVoiceInputError("");
    setIsListening(true);
    setOrbMode("processing");
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch (error) {
      recognitionRef.current = null;
      setIsListening(false);
      setOrbMode("idle");
      setVoiceInputError(
        error instanceof Error ? error.message : "Unable to start voice input."
      );
    }
  };

  return (
    <div className="flex h-screen min-w-0 overflow-hidden border border-cyan-500/20 bg-[#050b14] font-sans text-slate-100">
      {/* Sidebar */}
      <aside className="z-20 flex w-16 shrink-0 flex-col items-center border-r border-orange-500/20 bg-[#081018] px-2 py-4 shadow-2xl sm:w-56 sm:px-4 sm:py-8">
        <div className="flex w-full flex-col items-center">
          <div
            className="relative h-12 w-12 sm:h-40 sm:w-40"
            role="img"
            aria-label={`Saraswati energy orb: ${orbMode}`}
          >
            <SaraswatiOrb mode={orbMode} pulse={orbPulse} />
            <div
              className={`absolute right-2 top-2 h-2 w-2 rounded-full ${
                orbMode === "speaking"
                  ? "animate-ping bg-amber-300"
                  : orbMode === "processing"
                  ? "animate-pulse bg-orange-400"
                  : "bg-orange-300"
              }`}
            />
          </div>
          <span
            className={`mt-3 text-center font-mono text-[8px] uppercase tracking-wider sm:text-[10px] sm:tracking-[0.2em] ${
              orbMode === "speaking"
                ? "text-amber-300"
                : orbMode === "processing"
                ? "text-orange-400"
                : "text-orange-200/70"
            }`}
          >
            {orbMode === "speaking"
              ? "Voice Output Active"
              : orbMode === "processing"
              ? "Neural Processing"
              : "Core Standby"}
          </span>
        </div>
      </aside>

      {/* Main App Area */}
      <main className="flex min-w-0 flex-1 flex-col bg-[#050b14]">
        <header className="z-20 flex h-12 shrink-0 items-center justify-between border-b border-cyan-500/20 bg-[#081324]/95 px-6 font-mono text-xs text-cyan-400/80">
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                loading ? "animate-pulse bg-amber-400" : "animate-ping bg-cyan-400"
              }`}
            />
            <span>SYSTEM STATUS: ONLINE [LOCAL HOST]</span>
          </div>
          <div>{loading ? "PLANNING..." : plannerMode}</div>
        </header>

        <section className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="relative z-10 min-h-0 flex-1 space-y-4 overflow-y-auto p-6" aria-live="polite">
            {messages.map((message, index) => (
              <div
                key={`${index}-${message.sender}`}
                className={`flex flex-col ${
                  message.sender === "user" ? "items-end" : "items-start"
                }`}
              >
                <div
                  className={`max-w-xl rounded-xl px-5 py-3.5 font-mono text-sm leading-relaxed ${
                    message.sender === "user"
                      ? "rounded-br-none border border-cyan-400/30 bg-cyan-600/90 text-white shadow-lg shadow-cyan-900/40"
                      : "rounded-bl-none border border-cyan-500/30 bg-[#0a182f] text-slate-200 shadow-xl"
                  }`}
                >
                  <p className="whitespace-pre-wrap wrap-break-word">{message.text}</p>

                  {message.terminal_output && (
                    <pre className="mt-3 max-w-full overflow-x-auto whitespace-pre-wrap wrap-break-word rounded border border-cyan-900/50 bg-[#050b14] p-3 text-xs text-slate-300">
                      {message.terminal_output}
                    </pre>
                  )}

                  {message.plan && message.plan.length > 0 && (
                    <ol className="mt-3 space-y-1 border-l border-orange-400/50 pl-3 text-xs text-orange-100">
                      {message.plan.map((step, stepIndex) => (
                        <li key={`${step.intent}-${stepIndex}`}>
                          {stepIndex + 1}. {step.description} — {step.status}
                        </li>
                      ))}
                    </ol>
                  )}

                  {message.pendingAction && (
                    <form
                      className="mt-4 space-y-3 rounded-lg border border-orange-400/40 bg-[#17130e] p-3"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void sendConfirmedEmail(index, message.pendingAction!);
                      }}
                    >
                      <p className="text-xs font-semibold text-orange-200">
                        Review this email. Selecting “Send Email” opens a visible
                        Gmail window and sends this exact draft.
                      </p>
                      {!message.pendingAction.recipient && (
                        <p className="text-xs text-amber-200">
                          Enter the recipient’s full email address; Saraswati will
                          not guess a contact from a first name.
                        </p>
                      )}
                      <label className="block text-xs text-slate-300">
                        Recipient
                        <input
                          type="email"
                          required
                          value={message.pendingAction.recipient}
                          onChange={(event) =>
                            updatePendingEmail(
                              message.pendingAction!.id,
                              "recipient",
                              event.target.value
                            )
                          }
                          className="mt-1 w-full rounded border border-orange-900/60 bg-[#050b14] px-3 py-2 text-sm text-slate-100"
                        />
                      </label>
                      <label className="block text-xs text-slate-300">
                        Subject
                        <input
                          required
                          value={message.pendingAction.subject}
                          onChange={(event) =>
                            updatePendingEmail(
                              message.pendingAction!.id,
                              "subject",
                              event.target.value
                            )
                          }
                          className="mt-1 w-full rounded border border-orange-900/60 bg-[#050b14] px-3 py-2 text-sm text-slate-100"
                        />
                      </label>
                      <label className="block text-xs text-slate-300">
                        Message
                        <textarea
                          required
                          rows={5}
                          value={message.pendingAction.body}
                          onChange={(event) =>
                            updatePendingEmail(
                              message.pendingAction!.id,
                              "body",
                              event.target.value
                            )
                          }
                          className="mt-1 w-full resize-y rounded border border-orange-900/60 bg-[#050b14] px-3 py-2 text-sm text-slate-100"
                        />
                      </label>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="submit"
                          disabled={confirmingActionId === message.pendingAction.id}
                          className="rounded border border-orange-300/60 bg-orange-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-orange-500 disabled:opacity-50"
                        >
                          {confirmingActionId === message.pendingAction.id
                            ? "OPENING GMAIL..."
                            : "SEND EMAIL"}
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            void cancelPendingEmail(index, message.pendingAction!)
                          }
                          disabled={confirmingActionId === message.pendingAction.id}
                          className="rounded border border-slate-600 px-3 py-2 text-xs text-slate-200 hover:bg-slate-800"
                        >
                          Cancel draft
                        </button>
                      </div>
                    </form>
                  )}

                  {/* Speak Replay Button */}
                  {message.sender === "saraswati" && (
                    <button
                      type="button"
                      onClick={() => speakText(message.text)}
                      className="mt-2.5 flex items-center gap-1.5 rounded bg-cyan-950/60 px-2.5 py-1 font-mono text-[10px] text-cyan-300 transition hover:bg-cyan-900 border border-cyan-800/50"
                      title="Replay speech"
                    >
                      <span>🔊 Speak</span>
                    </button>
                  )}

                  {message.intent && (
                    <span className="mt-2 block font-mono text-[10px] uppercase tracking-widest text-cyan-400 opacity-80">
                      INTENT: {message.intent}
                    </span>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-2 px-2 font-mono text-xs text-cyan-400">
                <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-400" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-400" style={{ animationDelay: "0.2s" }} />
                <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-400" style={{ animationDelay: "0.4s" }} />
                <span>PROCESSING COMMAND VIA NEURAL ENGINE...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </section>

        {/* Command input */}
        <form onSubmit={handleSubmit} className="z-20 flex shrink-0 gap-2 border-t border-cyan-500/30 bg-[#081324] p-2 sm:gap-3 sm:p-4">
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Enter command or query for Saraswati..."
            aria-label="Command or query for Saraswati"
            className="min-w-0 flex-1 rounded-xl border border-cyan-500/30 bg-[#050b14] px-2 py-3 font-mono text-xs text-cyan-100 placeholder-slate-500 transition focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 sm:px-4 sm:text-sm"
          />
          <button
            type="button"
            onClick={toggleListening}
            aria-pressed={isListening}
            aria-label={isListening ? "Stop voice input" : "Start voice input"}
            className={`shrink-0 rounded-xl border px-2 py-3 font-mono text-xs transition sm:px-3 ${
              isListening
                ? "border-orange-300 bg-orange-600 text-white"
                : "border-cyan-500/30 bg-[#0d1b32] text-cyan-200 hover:border-orange-400/60"
            }`}
          >
            <span className="sm:hidden">{isListening ? "■" : "🎙️"}</span>
            <span className="hidden sm:inline">{isListening ? "■ Stop" : "🎙️ Voice Input"}</span>
          </button>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-xl border border-cyan-400/40 bg-cyan-600 px-3 py-3 font-mono text-xs font-medium text-white shadow-lg shadow-cyan-900/40 transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50 sm:px-6 sm:text-sm"
          >
            {loading ? "PROCESSING" : "SEND"}
          </button>
        </form>
        {voiceInputError && (
          <p role="status" className="px-4 pb-3 text-right font-mono text-xs text-amber-300">
            {voiceInputError}
          </p>
        )}
      </main>
    </div>
  );
}

export default App;