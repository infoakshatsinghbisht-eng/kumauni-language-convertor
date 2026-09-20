// Kumaoni Voice AI - Full-Stack Client App
// Connects to Kumaoni Language Standard Library API

document.addEventListener("DOMContentLoaded", () => {
  // =========================================================
  // 0. SYSTEM VOICE PRELOADER & AUDIO UNLOCK
  // =========================================================
  let systemVoices = [];

  function loadSystemVoices() {
    if ('speechSynthesis' in window) {
      systemVoices = window.speechSynthesis.getVoices();
    }
  }

  loadSystemVoices();
  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = () => {
      loadSystemVoices();
    };
  }

  // Unlock AudioContext on first user touch/click to prevent autoplay blocks
  document.body.addEventListener("click", () => {
    if ('speechSynthesis' in window && window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }
  }, { once: true });

  // =========================================================
  // 1. NAVIGATION & SUB-TABS
  // =========================================================
  const navTabs = document.querySelectorAll(".nav-tab");
  const tabPanes = document.querySelectorAll(".tab-pane");

  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const target = tab.getAttribute("data-tab");
      navTabs.forEach(t => t.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      const targetPane = document.getElementById(`tab-${target}`);
      if (targetPane) targetPane.classList.add("active");

      // Lazy load tab data
      if (target === "phraseboard") loadPhrases("all");
      if (target === "wisdom") loadWisdomData();
      if (target === "calendar") loadCalendarData();
    });
  });

  // Wisdom Subtab switching
  const wisdomPills = document.querySelectorAll(".subnav-pill");
  const wisdomSubpanes = document.querySelectorAll(".subtab-pane");

  wisdomPills.forEach(pill => {
    pill.addEventListener("click", () => {
      const target = pill.getAttribute("data-subtab");
      wisdomPills.forEach(p => p.classList.remove("active"));
      wisdomSubpanes.forEach(s => s.classList.remove("active"));
      pill.classList.add("active");
      const subPane = document.getElementById(`subtab-pane-${target}`);
      if (subPane) subPane.classList.add("active");
    });
  });

  // =========================================================
  // 2. HEALTH & TELEMETRY
  // =========================================================
  const statusBadge = document.getElementById("backend-status-badge");
  const badgeCorpusWords = document.getElementById("badge-corpus-words");
  const badgeSeason = document.getElementById("badge-season");

  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      if (data.status === "healthy") {
        if (statusBadge) {
          statusBadge.innerHTML = `<span class="pulse-dot"></span> API Online (v${data.library_version || data.version})`;
        }
        if (badgeCorpusWords && data.total_morph_words) {
          badgeCorpusWords.textContent = `📚 ${data.total_morph_words.toLocaleString()} Forms`;
        }
        if (badgeSeason && data.current_season) {
          badgeSeason.textContent = `🍂 ${data.current_season}`;
        }
      }
    } catch (e) {
      if (statusBadge) {
        statusBadge.innerHTML = `<span class="pulse-dot" style="background:#f43f5e"></span> API Offline`;
        statusBadge.classList.remove("badge-pulse");
        statusBadge.style.borderColor = "rgba(244, 63, 94, 0.4)";
        statusBadge.style.color = "#f43f5e";
      }
    }
  }
  checkHealth();

  // =========================================================
  // 3. SPEECH-TO-SPEECH TRANSLATOR
  // =========================================================
  const btnVoiceMic = document.getElementById("btn-voice-mic");
  const micStatusText = document.getElementById("mic-status-text");
  const voiceSourceLang = document.getElementById("voice-source-lang");
  const voiceTargetDialect = document.getElementById("voice-target-dialect");
  const toggleAutoSpeak = document.getElementById("toggle-autospeak");
  const voiceInputText = document.getElementById("voice-input-text");
  const speechLangTag = document.getElementById("speech-lang-tag");
  const btnVoiceTranslateManual = document.getElementById("btn-voice-translate-manual");
  const btnVoiceClear = document.getElementById("btn-voice-clear");

  const voiceOutputKumaoni = document.getElementById("voice-output-kumaoni");
  const voiceOutputRoman = document.getElementById("voice-output-roman");
  const voiceSyllableChips = document.getElementById("voice-syllable-chips");
  const tokenChipsContainer = document.getElementById("token-chips");
  const btnPlayKumaoniSpeech = document.getElementById("btn-play-kumaoni-speech");
  const btnPlayKumaoniWav = document.getElementById("btn-play-kumaoni-wav");
  const btnCopyVoiceKmy = document.getElementById("btn-copy-voice-kmy");
  const playBtnText = document.getElementById("play-btn-text");

  const canvas = document.getElementById("audio-visualizer-canvas");
  const ctx = canvas ? canvas.getContext("2d") : null;

  let isRecording = false;
  let recognition = null;
  let currentSpeed = 1.0;
  let lastKumaoniText = "ईजा कहाँ छ?";
  let lastRomanText = "Ija kahaan chha?";
  let lastAudioWavB64 = null;
  let visualizerAnimId = null;

  // Web Speech Recognition setup
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      isRecording = true;
      if (btnVoiceMic) btnVoiceMic.classList.add("recording");
      if (micStatusText) {
        micStatusText.textContent = "Listening... Speak now";
        micStatusText.className = "mic-status-text recording";
      }
      startVisualizerAnimation(true);
    };

    recognition.onresult = (event) => {
      let interim = "";
      let final = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          final += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      if (interim && voiceInputText) voiceInputText.value = interim;
      if (final && voiceInputText) {
        voiceInputText.value = final;
        handleVoiceTranslation(final);
      }
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      stopRecording();
      if (micStatusText) {
        micStatusText.textContent = event.error === "not-allowed" 
          ? "Microphone access denied. Type text above."
          : "Click Microphone to Speak";
      }
    };

    recognition.onend = () => {
      stopRecording();
    };
  } else {
    if (micStatusText) micStatusText.textContent = "Speech recognition unavailable in this browser. Type text below.";
  }

  function startRecording() {
    if (!recognition) {
      alert("Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.");
      return;
    }
    try {
      recognition.lang = voiceSourceLang ? voiceSourceLang.value : "en-IN";
      recognition.start();
    } catch (e) {
      console.error(e);
    }
  }

  function stopRecording() {
    isRecording = false;
    if (btnVoiceMic) btnVoiceMic.classList.remove("recording");
    if (micStatusText) {
      micStatusText.textContent = "Click Microphone to Speak";
      micStatusText.className = "mic-status-text";
    }
    stopVisualizerAnimation();
  }

  if (btnVoiceMic) {
    btnVoiceMic.addEventListener("click", () => {
      if (isRecording) {
        if (recognition) recognition.stop();
        stopRecording();
      } else {
        startRecording();
      }
    });
  }

  if (voiceSourceLang) {
    voiceSourceLang.addEventListener("change", () => {
      if (speechLangTag) speechLangTag.textContent = voiceSourceLang.options[voiceSourceLang.selectedIndex].text;
    });
  }

  // Quick Prompt Chips handler
  document.querySelectorAll(".prompt-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const text = chip.getAttribute("data-text");
      if (voiceInputText) {
        voiceInputText.value = text;
        handleVoiceTranslation(text);
      }
    });
  });

  // Speed controls
  document.querySelectorAll(".speed-chip").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".speed-chip").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentSpeed = parseFloat(btn.getAttribute("data-speed")) || 1.0;
    });
  });

  // Manual Translate button
  if (btnVoiceTranslateManual) {
    btnVoiceTranslateManual.addEventListener("click", () => {
      const txt = voiceInputText ? voiceInputText.value.trim() : "";
      if (txt) handleVoiceTranslation(txt);
    });
  }

  if (btnVoiceClear) {
    btnVoiceClear.addEventListener("click", () => {
      if (voiceInputText) voiceInputText.value = "";
    });
  }

  // Copy Translation
  if (btnCopyVoiceKmy) {
    btnCopyVoiceKmy.addEventListener("click", () => {
      if (lastKumaoniText) {
        navigator.clipboard.writeText(lastKumaoniText);
        btnCopyVoiceKmy.textContent = "✓";
        setTimeout(() => { btnCopyVoiceKmy.textContent = "📋"; }, 1500);
      }
    });
  }

  // Play Kumaoni Speech synthesis
  if (btnPlayKumaoniSpeech) {
    btnPlayKumaoniSpeech.addEventListener("click", () => {
      speakKumaoniVoice(lastKumaoniText, lastRomanText, currentSpeed);
    });
  }

  // Play synthesized PCM Tone Waveform
  if (btnPlayKumaoniWav) {
    btnPlayKumaoniWav.addEventListener("click", () => {
      if (lastAudioWavB64) {
        playBase64Wav(lastAudioWavB64);
      } else {
        const audio = new Audio(`/api/voice/wav?duration=0.5&freq=440`);
        audio.play().catch(e => console.warn(e));
      }
    });
  }

  async function handleVoiceTranslation(inputText) {
    if (!inputText || !inputText.trim()) return;

    const sourceLang = voiceSourceLang ? voiceSourceLang.value.split("-")[0] : "en";
    const dialect = voiceTargetDialect ? voiceTargetDialect.value : "central";

    if (voiceOutputKumaoni) voiceOutputKumaoni.textContent = "अनुवाद हुँदैछ... (Translating...)";

    try {
      const res = await fetch("/api/voice/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: inputText,
          source_lang: sourceLang,
          target_dialect: dialect,
          method: "auto",
          generate_audio: true
        })
      });

      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();

      lastKumaoniText = data.translated_text;
      lastRomanText = data.romanized;
      lastAudioWavB64 = data.audio_wav_base64;

      if (voiceOutputKumaoni) voiceOutputKumaoni.textContent = data.translated_text;
      if (voiceOutputRoman) voiceOutputRoman.textContent = data.romanized;

      // Render syllables
      if (voiceSyllableChips && data.syllables) {
        voiceSyllableChips.innerHTML = "";
        data.syllables.forEach((syl, idx) => {
          if (idx > 0) {
            const dot = document.createElement("span");
            dot.className = "syl-dot";
            dot.innerHTML = "&bull;";
            voiceSyllableChips.appendChild(dot);
          }
          const span = document.createElement("span");
          span.className = "syl-chip";
          span.textContent = syl;
          voiceSyllableChips.appendChild(span);
        });
      }

      // Render tokens grammar analysis
      if (tokenChipsContainer && data.tokens_analysis) {
        tokenChipsContainer.innerHTML = "";
        data.tokens_analysis.forEach(item => {
          const chip = document.createElement("span");
          chip.className = "token-chip";
          const meaningText = item.meaning ? ` • ${item.meaning}` : "";
          chip.innerHTML = `<span class="token-word">${item.token}</span> <span class="token-pos">${item.pos}${meaningText}</span>`;
          tokenChipsContainer.appendChild(chip);
        });
      }

      // Auto-speak if enabled
      if (toggleAutoSpeak && toggleAutoSpeak.checked) {
        speakKumaoniVoice(data.translated_text, data.romanized, currentSpeed);
      }

      // Add to Session History
      addToHistory({
        source_text: inputText,
        translated_text: data.translated_text,
        romanized: data.romanized,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      });

    } catch (err) {
      console.error("Translation error:", err);
      if (voiceOutputKumaoni) voiceOutputKumaoni.textContent = "त्रुटि (Translation error)";
    }
  }

  // Visualizer Animation
  function startVisualizerAnimation(active = false) {
    if (!ctx || !canvas) return;
    let phase = 0;

    function render() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      ctx.lineWidth = 2.5;
      ctx.strokeStyle = active ? "#f59e0b" : "rgba(245, 158, 11, 0.4)";
      ctx.beginPath();

      const bars = 36;
      const barWidth = width / bars;

      for (let i = 0; i < bars; i++) {
        const x = i * barWidth;
        const amplitude = active 
          ? Math.sin(phase + i * 0.35) * 35 * (Math.sin(phase * 0.8 + i) * 0.5 + 0.5)
          : Math.sin(phase + i * 0.2) * 8;
        
        ctx.fillStyle = active 
          ? `hsla(${38 + i * 2}, 95%, 55%, 0.85)` 
          : "rgba(245, 158, 11, 0.25)";
        
        const bHeight = Math.abs(amplitude) + 4;
        ctx.fillRect(x + 2, centerY - bHeight / 2, barWidth - 4, bHeight);
      }

      phase += 0.08;
      visualizerAnimId = requestAnimationFrame(render);
    }
    cancelAnimationFrame(visualizerAnimId);
    render();
  }

  function stopVisualizerAnimation() {
    startVisualizerAnimation(false);
  }
  startVisualizerAnimation(false);

  // =========================================================
  // 4. ROCK-SOLID SPEECH SYNTHESIS ENGINE
  // =========================================================
  function speakKumaoniVoice(kumaoniText, romanText = "", rate = 1.0) {
    if (!('speechSynthesis' in window)) {
      console.warn("Speech synthesis is not supported in this browser.");
      if (lastAudioWavB64) playBase64Wav(lastAudioWavB64);
      return;
    }

    try {
      window.speechSynthesis.cancel();
      window.speechSynthesis.resume();
    } catch (e) {
      console.warn("SpeechSynthesis resume error:", e);
    }

    loadSystemVoices();

    // Look for Indic (Hindi, Nepali, Marathi, Sanskrit, India) voice
    const indicVoice = systemVoices.find(v => {
      const l = (v.lang || "").toLowerCase();
      const n = (v.name || "").toLowerCase();
      return l.startsWith("hi") ||
             l.startsWith("ne") ||
             l.startsWith("mr") ||
             l.startsWith("sa") ||
             l.includes("in") ||
             n.includes("hindi") ||
             n.includes("india") ||
             n.includes("swara") ||
             n.includes("kalpana") ||
             n.includes("hemant") ||
             n.includes("neerja") ||
             n.includes("madhav");
    });

    let textToSpeak = kumaoniText;
    let targetLang = "hi-IN";

    // If no Indic voice installed on user's OS, speak Romanized phonetics using English voice
    if (!indicVoice) {
      textToSpeak = romanText || kumaoniText;
      targetLang = "en-IN";
    }

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = targetLang;

    if (indicVoice) {
      utterance.voice = indicVoice;
    } else if (systemVoices.length > 0) {
      const engVoice = systemVoices.find(v => (v.lang || "").toLowerCase().startsWith("en")) || systemVoices[0];
      if (engVoice) utterance.voice = engVoice;
    }

    utterance.rate = Math.max(0.6, Math.min(1.5, rate * 0.94));
    utterance.pitch = 1.05;

    if (playBtnText) playBtnText.textContent = "🔊 Speaking...";
    startVisualizerAnimation(true);

    utterance.onend = () => {
      if (playBtnText) playBtnText.textContent = "Speak Kumaoni";
      stopVisualizerAnimation();
    };

    utterance.onerror = (err) => {
      console.warn("SpeechSynthesis utterance error:", err);
      if (playBtnText) playBtnText.textContent = "Speak Kumaoni";
      stopVisualizerAnimation();
      // Fallback to Tone WAV if speech engine errors
      if (lastAudioWavB64) {
        playBase64Wav(lastAudioWavB64);
      }
    };

    // Small delay to prevent Chromium cancellation race condition
    setTimeout(() => {
      try {
        window.speechSynthesis.speak(utterance);
      } catch (e) {
        console.warn("speechSynthesis.speak failed:", e);
        if (lastAudioWavB64) playBase64Wav(lastAudioWavB64);
      }
    }, 60);
  }

  function playBase64Wav(b64Data) {
    if (!b64Data) return;
    try {
      const snd = new Audio("data:audio/wav;base64," + b64Data);
      startVisualizerAnimation(true);
      snd.onended = () => stopVisualizerAnimation();
      snd.onerror = () => stopVisualizerAnimation();
      snd.play().catch(e => {
        console.warn("Audio wav playback catch:", e);
        stopVisualizerAnimation();
      });
    } catch (e) {
      console.warn("Audio wav playback error:", e);
    }
  }

  // =========================================================
  // 5. TWO-WAY DIALOGUE MODE
  // =========================================================
  const dialogueVisitorInput = document.getElementById("dialogue-visitor-input");
  const dialogueNativeInput = document.getElementById("dialogue-native-input");
  const btnDialogueVisitorSpeak = document.getElementById("btn-dialogue-visitor-speak");
  const btnDialogueNativeSpeak = document.getElementById("btn-dialogue-native-speak");
  const btnDialogueVisitorMic = document.getElementById("btn-dialogue-visitor-mic");
  const btnDialogueNativeMic = document.getElementById("btn-dialogue-native-mic");
  const dialogueFeed = document.getElementById("dialogue-feed");
  const btnClearDialogue = document.getElementById("btn-clear-dialogue");

  if (btnDialogueVisitorSpeak) {
    btnDialogueVisitorSpeak.addEventListener("click", () => {
      const msg = dialogueVisitorInput ? dialogueVisitorInput.value.trim() : "";
      if (msg) executeDialogueExchange("person_a", msg, "en");
    });
  }

  if (btnDialogueNativeSpeak) {
    btnDialogueNativeSpeak.addEventListener("click", () => {
      const msg = dialogueNativeInput ? dialogueNativeInput.value.trim() : "";
      if (msg) executeDialogueExchange("person_b", msg, "kmy");
    });
  }

  if (btnClearDialogue && dialogueFeed) {
    btnClearDialogue.addEventListener("click", () => {
      dialogueFeed.innerHTML = "";
    });
  }

  async function executeDialogueExchange(speaker, message, lang) {
    try {
      const res = await fetch("/api/voice/dialogue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          speaker, 
          message, 
          source_lang: lang, 
          target_dialect: voiceTargetDialect ? voiceTargetDialect.value : "central" 
        })
      });
      const data = await res.json();
      renderDialogueBubble(data);

      speakKumaoniVoice(data.translated_kumaoni, data.romanized, 1.0);
    } catch (e) {
      console.error("Dialogue error:", e);
    }
  }

  function renderDialogueBubble(data) {
    if (!dialogueFeed) return;
    const isVisitor = data.speaker === "person_a";
    const bubble = document.createElement("div");
    bubble.className = `dialogue-bubble ${isVisitor ? "bubble-visitor" : "bubble-native"}`;

    const title = isVisitor ? "🎒 Visitor (Tourist)" : "🏔️ Local Resident (पहाड़ी)";
    const mainText = isVisitor ? data.translated_kumaoni : data.original;
    const subText = isVisitor 
      ? `Original: "${data.original}" • ${data.romanized}` 
      : `English: "${data.translated_english}" • ${data.romanized}`;

    bubble.innerHTML = `
      <div class="bubble-header">
        <span class="bubble-sender">${title}</span>
        <button class="bubble-play-btn" title="Play Speech">🔊</button>
      </div>
      <div class="bubble-main-text">${mainText}</div>
      <div class="bubble-sub-text">${subText}</div>
    `;

    const playBtn = bubble.querySelector(".bubble-play-btn");
    if (playBtn) {
      playBtn.addEventListener("click", () => {
        speakKumaoniVoice(mainText, data.romanized, 1.0);
      });
    }

    dialogueFeed.appendChild(bubble);
    dialogueFeed.scrollTop = dialogueFeed.scrollHeight;
  }

  // =========================================================
  // 6. MOUNTAIN PHRASEBOARD
  // =========================================================
  const phraseGrid = document.getElementById("voice-phrase-grid");
  const phraseCatTabs = document.querySelectorAll(".pcat-tab");
  const phraseSearchInput = document.getElementById("phrase-search-input");

  let currentPhraseCat = "all";

  phraseCatTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      phraseCatTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentPhraseCat = tab.getAttribute("data-cat");
      loadPhrases(currentPhraseCat, phraseSearchInput ? phraseSearchInput.value : "");
    });
  });

  if (phraseSearchInput) {
    phraseSearchInput.addEventListener("input", () => {
      loadPhrases(currentPhraseCat, phraseSearchInput.value);
    });
  }

  async function loadPhrases(category = "all", query = "") {
    if (!phraseGrid) return;
    phraseGrid.innerHTML = `<div class="loading-state">Loading mountain phrases...</div>`;

    try {
      let url = `/api/voice/phrases?category=${encodeURIComponent(category)}`;
      if (query.trim()) {
        url += `&query=${encodeURIComponent(query.trim())}`;
      }
      const res = await fetch(url);
      const data = await res.json();

      if (!data.phrases || data.phrases.length === 0) {
        phraseGrid.innerHTML = `<div class="empty-state">No phrases found for "${query || category}".</div>`;
        return;
      }

      phraseGrid.innerHTML = "";
      data.phrases.forEach(p => {
        const card = document.createElement("div");
        card.className = "phrase-card";
        card.innerHTML = `
          <div class="phrase-top">
            <span class="phrase-cat-tag">${p.category || 'dialogue'}</span>
            <button class="btn-play-phrase" title="Listen to Phrase">🔊</button>
          </div>
          <div class="phrase-kumaoni">${p.kumaoni}</div>
          <div class="phrase-roman">${p.roman || ''}</div>
          <div class="phrase-english"><strong>English:</strong> ${p.english}</div>
          ${p.hindi ? `<div class="phrase-hindi"><strong>हिन्दी:</strong> ${p.hindi}</div>` : ''}
        `;

        const playBtn = card.querySelector(".btn-play-phrase");
        playBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          speakKumaoniVoice(p.kumaoni, p.roman, 1.0);
        });

        card.addEventListener("click", () => {
          speakKumaoniVoice(p.kumaoni, p.roman, 1.0);
          if (voiceInputText) {
            voiceInputText.value = p.english;
          }
        });

        phraseGrid.appendChild(card);
      });
    } catch (e) {
      console.error("Error loading phrases:", e);
      phraseGrid.innerHTML = `<div class="error-state">Failed to load phrases.</div>`;
    }
  }

  // =========================================================
  // 7. HIMALAYAN WISDOM (PROVERBS, RIDDLES, LITERATURE)
  // =========================================================
  const proverbsGrid = document.getElementById("proverbs-grid");
  const proverbsSearchInput = document.getElementById("proverb-search-input");
  const proverbsCountBadge = document.getElementById("proverbs-count-badge");
  const riddlesGrid = document.getElementById("riddles-grid");
  const litGrid = document.getElementById("literature-content-grid");

  let wisdomLoaded = false;

  async function loadWisdomData() {
    if (wisdomLoaded) return;
    wisdomLoaded = true;
    loadProverbs();
    loadRiddles();
    loadLiterature();
  }

  if (proverbsSearchInput) {
    proverbsSearchInput.addEventListener("input", () => {
      loadProverbs(proverbsSearchInput.value);
    });
  }

  async function loadProverbs(query = "") {
    if (!proverbsGrid) return;
    proverbsGrid.innerHTML = `<div class="loading-state">Loading Himalayan proverbs...</div>`;

    try {
      let url = "/api/culture/proverbs";
      if (query.trim()) url += `?query=${encodeURIComponent(query.trim())}`;
      const res = await fetch(url);
      const data = await res.json();

      if (proverbsCountBadge) proverbsCountBadge.textContent = `${data.total || data.count} Proverbs`;

      if (!data.proverbs || data.proverbs.length === 0) {
        proverbsGrid.innerHTML = `<div class="empty-state">No proverbs matching "${query}".</div>`;
        return;
      }

      proverbsGrid.innerHTML = "";
      data.proverbs.forEach(prov => {
        const card = document.createElement("div");
        card.className = "wisdom-card proverb-card";
        card.innerHTML = `
          <div class="wisdom-card-header">
            <span class="wisdom-tag">📜 अखाण (Proverb)</span>
            <button class="btn-play-wisdom" title="Listen">🔊</button>
          </div>
          <div class="wisdom-kumaoni">${prov.kumaoni}</div>
          <div class="wisdom-roman">${prov.roman || ''}</div>
          <div class="wisdom-meaning">
            <strong>Meaning:</strong> ${prov.meaning_en || prov.meaning}
          </div>
          ${prov.meaning_hi ? `<div class="wisdom-hindi"><strong>हिन्दी अर्थ:</strong> ${prov.meaning_hi}</div>` : ''}
        `;

        card.querySelector(".btn-play-wisdom").addEventListener("click", () => {
          speakKumaoniVoice(prov.kumaoni, prov.roman, 0.95);
        });

        proverbsGrid.appendChild(card);
      });
    } catch (e) {
      console.error(e);
      proverbsGrid.innerHTML = `<div class="error-state">Failed to load proverbs.</div>`;
    }
  }

  async function loadRiddles() {
    if (!riddlesGrid) return;
    riddlesGrid.innerHTML = `<div class="loading-state">Loading mountain riddles...</div>`;

    try {
      const res = await fetch("/api/culture/riddles");
      const data = await res.json();

      if (!data.riddles || data.riddles.length === 0) {
        riddlesGrid.innerHTML = `<div class="empty-state">No riddles available.</div>`;
        return;
      }

      riddlesGrid.innerHTML = "";
      data.riddles.forEach((rid, idx) => {
        const card = document.createElement("div");
        card.className = "wisdom-card riddle-card";
        card.innerHTML = `
          <div class="wisdom-card-header">
            <span class="wisdom-tag">🧩 आणा #${idx + 1} (Riddle)</span>
            <button class="btn-play-riddle" title="Listen to Riddle">🔊</button>
          </div>
          <div class="wisdom-kumaoni riddle-q">${rid.kumaoni || rid.riddle}</div>
          <div class="wisdom-roman">${rid.roman || ''}</div>
          <div class="riddle-english">"${rid.meaning_en || rid.clue || ''}"</div>
          
          <div class="riddle-answer-section">
            <button class="btn btn-outline btn-sm btn-reveal-answer">👁️ Reveal Answer</button>
            <div class="riddle-answer-hidden">
              <span class="ans-label">Answer (उत्तर):</span>
              <span class="ans-kumaoni">${rid.answer_kumaoni || rid.answer || ''}</span>
              <span class="ans-en">(${rid.answer_en || ''})</span>
            </div>
          </div>
        `;

        const btnReveal = card.querySelector(".btn-reveal-answer");
        const ansHidden = card.querySelector(".riddle-answer-hidden");
        btnReveal.addEventListener("click", () => {
          ansHidden.classList.toggle("revealed");
          btnReveal.textContent = ansHidden.classList.contains("revealed") ? "🙈 Hide Answer" : "👁️ Reveal Answer";
        });

        card.querySelector(".btn-play-riddle").addEventListener("click", () => {
          speakKumaoniVoice(rid.kumaoni || rid.riddle, rid.roman, 0.95);
        });

        riddlesGrid.appendChild(card);
      });
    } catch (e) {
      console.error(e);
      riddlesGrid.innerHTML = `<div class="error-state">Failed to load riddles.</div>`;
    }
  }

  async function loadLiterature() {
    if (!litGrid) return;
    litGrid.innerHTML = `<div class="loading-state">Loading Himalayan folk literature...</div>`;

    try {
      const res = await fetch("/api/culture/literature");
      const data = await res.json();

      litGrid.innerHTML = `
        <div class="lit-section">
          <h4 class="lit-section-title">🏔️ Legendary Folk Epics &amp; Tales</h4>
          <div class="lit-cards-row">
            <div class="lit-card">
              <h5>Malushahi &amp; Rajula (माळूशाही)</h5>
              <p>The timeless romantic ballad and heroic saga of Prince Malushahi of Vairat Pattan and Rajula of the Johar valley, immortalized in Himalayan folklore.</p>
            </div>
            <div class="lit-card">
              <h5>Ajuwa Bafol (अजुवा बफौल)</h5>
              <p>The valorous chivalric epic of the 52 mountain forts and warriors of the Katyuri era.</p>
            </div>
          </div>
        </div>

        <div class="lit-section mt-4">
          <h4 class="lit-section-title">✍️ Venerated Kumaoni Literary Figures</h4>
          <div class="lit-cards-row">
            <div class="lit-card">
              <h5>Gumani Pant (गुमानी पन्त)</h5>
              <p>1790–1846 &bull; The pioneer of Kumaoni poetry, creator of classic four-language verses bridging Sanskrit, Hindi, Nepali, and Kumaoni.</p>
            </div>
            <div class="lit-card">
              <h5>Gaurda (गौरीदत्त पाण्डे 'गौर्दा')</h5>
              <p>1872–1939 &bull; Renowned folk poet, freedom fighter, and creator of socially conscious Kumaoni verses.</p>
            </div>
            <div class="lit-card">
              <h5>Charu Chandra Pande</h5>
              <p>Pioneering linguist and compiler of Kumaoni grammar and dialectology treatises.</p>
            </div>
          </div>
        </div>
      `;
    } catch (e) {
      console.error(e);
      litGrid.innerHTML = `<div class="error-state">Failed to load literature.</div>`;
    }
  }

  // =========================================================
  // 8. KUMAONI CALENDAR & NUMBERS CONVERTER
  // =========================================================
  const monthsGrid = document.getElementById("calendar-months-grid");
  const calendarCurrentSeason = document.getElementById("calendar-current-season");
  const numConvertInput = document.getElementById("num-convert-input");
  const btnConvertNum = document.getElementById("btn-convert-num");
  const numResWords = document.getElementById("num-res-words");
  const numResRoman = document.getElementById("num-res-roman");
  const numResOrdinal = document.getElementById("num-res-ordinal");
  const numResDevDigits = document.getElementById("num-res-dev-digits");
  const btnPlayNumSpeech = document.getElementById("btn-play-num-speech");

  let calendarLoaded = false;

  async function loadCalendarData() {
    if (calendarLoaded) return;
    calendarLoaded = true;

    try {
      const res = await fetch("/api/culture/calendar");
      const data = await res.json();

      if (calendarCurrentSeason && data.current_season) {
        calendarCurrentSeason.textContent = data.current_season;
      }

      if (monthsGrid && data.months) {
        monthsGrid.innerHTML = "";
        const kumaoniMonthList = [
          { kmy: "चैत (Chait)", en: "Mar - Apr", num: 1 },
          { kmy: "बैसाख (Baisakh)", en: "Apr - May", num: 2 },
          { kmy: "जेठ (Jeth)", en: "May - Jun", num: 3 },
          { kmy: "असाढ़ (Asadh)", en: "Jun - Jul", num: 4 },
          { kmy: "साउन (Saun)", en: "Jul - Aug", num: 5 },
          { kmy: "भादो (Bhado)", en: "Aug - Sep", num: 6 },
          { kmy: "आसोज (Aasoj)", en: "Sep - Oct", num: 7 },
          { kmy: "कातिक (Katik)", en: "Oct - Nov", num: 8 },
          { kmy: "मंगसिर (Mangsir)", en: "Nov - Dec", num: 9 },
          { kmy: "पूस (Poos)", en: "Dec - Jan", num: 10 },
          { kmy: "माघ (Magh)", en: "Jan - Feb", num: 11 },
          { kmy: "फागुन (Phagun)", en: "Feb - Mar", num: 12 },
        ];

        kumaoniMonthList.forEach(m => {
          const item = document.createElement("div");
          item.className = "month-item";
          item.innerHTML = `
            <span class="month-num">${m.num}</span>
            <span class="month-kumaoni">${m.kmy}</span>
            <span class="month-gregorian">${m.en}</span>
          `;
          monthsGrid.appendChild(item);
        });
      }
    } catch (e) {
      console.error("Calendar load error:", e);
    }
  }

  if (btnConvertNum) {
    btnConvertNum.addEventListener("click", () => {
      convertKumaoniNumber();
    });
  }

  if (numConvertInput) {
    numConvertInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") convertKumaoniNumber();
    });
  }

  async function convertKumaoniNumber() {
    const val = parseInt(numConvertInput.value, 10);
    if (isNaN(val)) return;

    try {
      const res = await fetch("/api/numbers/convert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ number: val, form: "cardinal" })
      });
      const data = await res.json();

      if (numResWords) numResWords.textContent = data.words;
      if (numResRoman) numResRoman.textContent = data.roman;
      if (numResOrdinal) numResOrdinal.textContent = data.ordinal;
      if (numResDevDigits) numResDevDigits.textContent = data.devanagari_num;

      if (btnPlayNumSpeech) {
        btnPlayNumSpeech.onclick = () => speakKumaoniVoice(data.words, data.roman, 0.95);
      }
    } catch (e) {
      console.error(e);
    }
  }

  if (btnPlayNumSpeech) {
    btnPlayNumSpeech.addEventListener("click", () => {
      if (numResWords) speakKumaoniVoice(numResWords.textContent, numResRoman ? numResRoman.textContent : "", 0.95);
    });
  }

  // =========================================================
  // 9. SESSION HISTORY
  // =========================================================
  const historyList = document.getElementById("voice-history-list");
  const btnClearHistory = document.getElementById("btn-clear-history");
  let sessionHistory = [];

  function addToHistory(item) {
    sessionHistory.unshift(item);
    renderHistory();
  }

  function renderHistory() {
    if (!historyList) return;
    if (sessionHistory.length === 0) {
      historyList.innerHTML = `<div class="history-empty">No voice records yet. Click the microphone or pick a prompt to start speaking!</div>`;
      return;
    }

    historyList.innerHTML = "";
    sessionHistory.forEach(h => {
      const el = document.createElement("div");
      el.className = "history-item";
      el.innerHTML = `
        <div class="history-top">
          <span class="history-time">${h.time}</span>
          <button class="btn-play-history" title="Replay Speech">🔊 Replay</button>
        </div>
        <div class="history-src"><strong>Input:</strong> ${h.source_text}</div>
        <div class="history-trans">${h.translated_text}</div>
        <div class="history-roman">${h.romanized}</div>
      `;

      el.querySelector(".btn-play-history").addEventListener("click", () => {
        speakKumaoniVoice(h.translated_text, h.romanized, 1.0);
      });

      historyList.appendChild(el);
    });
  }

  if (btnClearHistory) {
    btnClearHistory.addEventListener("click", () => {
      sessionHistory = [];
      renderHistory();
    });
  }

});
