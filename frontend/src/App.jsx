import { useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowLeft, ArrowRight, Check, Copy, Plus, Radio, Sparkles, Users, X } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const blankQuestion = () => ({ prompt: '', choices: ['', '', '', ''], correct_choice_index: 0, time_limit_seconds: 20 });

async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : 'Please check the quiz details and try again.';
    throw new Error(detail);
  }
  return body;
}

function useLocationState() {
  return useState(() => ({ path: window.location.pathname, search: new URLSearchParams(window.location.search) }));
}

export default function App() {
  const [location, setLocation] = useLocationState();
  const [view, setView] = useState('create');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState(null);
  const [event, setEvent] = useState(null);
  const [hostInfo, setHostInfo] = useState(null);
  const [participant, setParticipant] = useState(null);
  const [joinForm, setJoinForm] = useState({ name: '', display_name: '' });
  const [title, setTitle] = useState('');
  const [questions, setQuestions] = useState([blankQuestion()]);

  const joinCode = location.search.get('join');
  const hostEventId = location.path.startsWith('/host/') ? location.path.split('/')[2] : null;
  const hostToken = useMemo(() => window.location.hash.slice(1), [hostEventId, location.path]);

  useEffect(() => {
    let alive = true;
    if (joinCode) {
      setView('join');
      api(`/api/events/${encodeURIComponent(joinCode)}`)
        .then((data) => alive && setEvent(data))
        .catch((reason) => alive && setError(reason.message));
    } else if (hostEventId) {
      setView('host');
      api(`/api/host/${hostEventId}`, { headers: { Authorization: `Bearer ${hostToken}` } })
        .then((data) => alive && setHostInfo(data))
        .catch((reason) => alive && setError(reason.message));
    } else {
      setView('create');
    }
    return () => { alive = false; };
  }, [joinCode, hostEventId, hostToken]);

  function navigate(path) {
    window.history.pushState({}, '', path);
    setLocation({ path: window.location.pathname, search: new URLSearchParams(window.location.search) });
    setError('');
  }

  function updateQuestion(questionIndex, updates) {
    setQuestions((items) => items.map((item, index) => index === questionIndex ? { ...item, ...updates } : item));
  }

  async function createQuiz(eventForm) {
    eventForm.preventDefault();
    setBusy(true);
    setError('');
    try {
      const cleanedQuestions = questions.map((question) => {
        const filled = question.choices
          .map((text, originalIndex) => ({ text: text.trim(), originalIndex }))
          .filter(({ text }) => text);
        const correct_choice_index = filled.findIndex(({ originalIndex }) => originalIndex === question.correct_choice_index);
        if (filled.length < 2) throw new Error('Each question needs at least two answer choices.');
        if (correct_choice_index < 0) throw new Error('Choose a correct answer that has text.');
        return { ...question, choices: filled.map(({ text }) => text), correct_choice_index };
      });
      const payload = { title, questions: cleanedQuestions };
      const result = await api('/api/quizzes', { method: 'POST', body: JSON.stringify(payload) });
      setCreated({ ...result, participant_url: new URL(result.participant_url, window.location.origin).href });
      setView('created');
    } catch (reason) {
      setError(reason.message);
    } finally {
      setBusy(false);
    }
  }

  async function joinQuiz(eventForm) {
    eventForm.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await api(`/api/events/${encodeURIComponent(joinCode)}/participants`, {
        method: 'POST', body: JSON.stringify(joinForm),
      });
      sessionStorage.setItem(`quiz:${joinCode}:reconnect`, result.reconnect_token);
      setParticipant(result);
    } catch (reason) {
      setError(reason.message);
    } finally {
      setBusy(false);
    }
  }

  async function copy(value) {
    try { await navigator.clipboard.writeText(value); } catch { setError('Clipboard access is unavailable. Copy the link manually.'); }
  }

  return (
    <main className="page-shell">
      <nav className="topbar">
        <button className="brand" onClick={() => navigate('/')} aria-label="Quiz Aura home">
          <span className="brand-mark"><Sparkles size={17} /></span><span>quiz<span className="brand-light">aura</span></span>
        </button>
        <span className="topbar-note"><span className="status-dot" /> LIVE QUIZ STUDIO</span>
      </nav>

      <section className="hero-wrap">
        {view === 'create' && <>
          <div className="eyebrow"><span className="eyebrow-line" />MAKE A MOMENT<span className="eyebrow-line" /></div>
          <h1>Bring your<br /><span className="gradient-text">people together.</span></h1>
          <p className="hero-copy">A little friendly competition goes a long way.<br className="desktop-break" /> Build a quiz and let the room light up.</p>
          <div className="hero-stamp"><span>01</span><span className="stamp-rule" /> CREATE YOUR QUIZ</div>
          <form className="builder" onSubmit={createQuiz}>
            <div className="builder-heading"><div><span className="section-kicker">THE SETUP</span><h2>Your quiz, your rules.</h2></div><span className="step-count">01 <i>/</i> 03</span></div>
            <label className="field-label" htmlFor="quiz-title">QUIZ TITLE</label>
            <input id="quiz-title" className="text-input title-input" maxLength="100" placeholder="e.g. Friday night trivia" value={title} onChange={(e) => setTitle(e.target.value)} required />
            {questions.map((question, qi) => <article className="question-editor" key={qi}>
              <div className="question-editor-top"><span className="question-number">QUESTION {String(qi + 1).padStart(2, '0')}</span>{questions.length > 1 && <button type="button" className="icon-button" onClick={() => setQuestions((items) => items.filter((_, index) => index !== qi))} aria-label="Remove question"><X size={16} /></button>}</div>
              <textarea className="text-input prompt-input" placeholder="Write your question..." maxLength="500" value={question.prompt} onChange={(e) => updateQuestion(qi, { prompt: e.target.value })} required />
              <div className="choice-grid">{question.choices.map((choice, ci) => <label className={`choice-field ${question.correct_choice_index === ci ? 'correct' : ''}`} key={ci}>
                <span className="choice-letter">{String.fromCharCode(65 + ci)}</span><input aria-label={`Answer ${String.fromCharCode(65 + ci)}`} maxLength="200" placeholder={`Answer ${String.fromCharCode(65 + ci)}`} value={choice} onChange={(e) => updateQuestion(qi, { choices: question.choices.map((value, index) => index === ci ? e.target.value : value) })} />
                <button type="button" className="correct-toggle" aria-label={`Mark answer ${String.fromCharCode(65 + ci)} correct`} aria-pressed={question.correct_choice_index === ci} onClick={() => updateQuestion(qi, { correct_choice_index: ci })}>{question.correct_choice_index === ci && <Check size={13} />}</button>
              </label>)}</div>
              <div className="question-footer"><span><span className="mini-dot" /> Tap the ring to mark the correct answer</span><label className="timer-select">TIMER <select value={question.time_limit_seconds} onChange={(e) => updateQuestion(qi, { time_limit_seconds: Number(e.target.value) })}>{[10, 15, 20, 30, 45, 60].map((n) => <option key={n} value={n}>{n}s</option>)}</select></label></div>
            </article>)}
            <div className="builder-actions"><button type="button" className="add-question" onClick={() => setQuestions((items) => [...items, blankQuestion()])} disabled={questions.length >= 20}><Plus size={16} /> Add another question <span>{questions.length}/20</span></button><button className="primary-button" type="submit" disabled={busy}>{busy ? 'Creating…' : <>Create quiz <ArrowRight size={17} /></>}</button></div>
            {error && <p className="error-message" role="alert">{error}</p>}
          </form>
        </>}

        {view === 'created' && created && <div className="result-panel">
          <div className="success-icon"><Check size={27} /></div><div className="eyebrow"><span className="eyebrow-line" />ROOM IS READY<span className="eyebrow-line" /></div>
          <h1>Let the game<br /><span className="gradient-text">find its people.</span></h1>
          <p className="hero-copy">Your quiz <strong>{created.title}</strong> is waiting in the lobby.</p>
          <div className="share-card"><span className="section-kicker">PARTICIPANT LINK</span><div className="share-value"><span>{created.participant_url}</span><button className="copy-button" onClick={() => copy(created.participant_url)}><Copy size={15} /> Copy</button></div><div className="join-code">JOIN CODE <strong>{created.join_code}</strong></div></div>
          <a className="primary-button host-button" href={created.host_url}>Open host lobby <ArrowRight size={17} /></a>
          <p className="private-note">Keep your host link private. Anyone with it can control this quiz.</p>
        </div>}

        {view === 'join' && <div className="join-wrap">
          <button className="back-link" onClick={() => navigate('/')}><ArrowLeft size={15} /> Create a quiz</button>
          {error && !event ? <div className="notice-card error-message" role="alert">{error}</div> : event && !participant ? <>
            <div className="eyebrow"><span className="eyebrow-line" />YOU’RE INVITED<span className="eyebrow-line" /></div>
            <h1 className="join-title">{event.title}<br /><span className="gradient-text">starts with you.</span></h1>
            <div className="join-meta"><span><Users size={16} /> {event.participant_count} here</span><span className="meta-divider" /><span>ROOM {event.join_code}</span></div>
            <form className="join-card" onSubmit={joinQuiz}>
              <h2>Save your seat.</h2><p>Pick a name your friends will recognize.</p>
              <label className="field-label" htmlFor="player-name">YOUR NAME</label><input id="player-name" className="text-input" maxLength="80" autoComplete="name" placeholder="Your name" value={joinForm.name} onChange={(e) => setJoinForm({ ...joinForm, name: e.target.value })} required />
              <label className="field-label" htmlFor="display-name">DISPLAY NAME</label><input id="display-name" className="text-input" maxLength="32" placeholder="How you’ll appear on the leaderboard" value={joinForm.display_name} onChange={(e) => setJoinForm({ ...joinForm, display_name: e.target.value })} required />
              {error && <p className="error-message" role="alert">{error}</p>}
              <button className="primary-button full-button" disabled={busy}>{busy ? 'Joining…' : <>Join the lobby <ArrowRight size={17} /></>}</button>
            </form>
          </> : participant && <div className="lobby-card"><span className="lobby-orbit"><Radio size={26} /></span><div className="eyebrow"><span className="eyebrow-line" />YOU’RE IN<span className="eyebrow-line" /></div><h1 className="lobby-title">Stay close,<br /><span className="gradient-text">{participant.display_name}.</span></h1><p className="hero-copy">You’re in the lobby for <strong>{event.title}</strong>.<br />The host will start the game soon.</p><div className="waiting-status"><span className="pulse-dot" /> WAITING FOR THE HOST</div></div>}
        </div>}

        {view === 'host' && <div className="host-wrap">
          {error && !hostInfo ? <div className="notice-card error-message" role="alert">{error}</div> : hostInfo && <>
            <div className="eyebrow"><span className="eyebrow-line" />HOST CONTROL<span className="eyebrow-line" /></div><h1 className="host-title">{hostInfo.title}<br /><span className="gradient-text">lobby.</span></h1>
            <div className="host-stats"><div className="stat-card"><span className="section-kicker">IN THE ROOM</span><strong>{String(hostInfo.participant_count).padStart(2, '0')}</strong><span className="stat-caption">of 50 players</span></div><div className="stat-card"><span className="section-kicker">JOIN CODE</span><strong className="stat-code">{hostInfo.join_code}</strong><button className="copy-inline" onClick={() => copy(hostInfo.join_code)}><Copy size={14} /> Copy code</button></div></div>
            <div className="players-card"><div className="players-heading"><div><span className="section-kicker">THE CROWD</span><h2>Players in the lobby</h2></div><span className="live-pill"><span className="status-dot" /> {hostInfo.state.toUpperCase()}</span></div>
              {hostInfo.participants.length ? <div className="player-list">{hostInfo.participants.map((player, index) => <div className="player-row" key={`${player.display_name}-${index}`}><span className="player-avatar">{player.display_name.slice(0, 1).toUpperCase()}</span><span>{player.display_name}</span><span className="player-private">{player.name}</span></div>)}</div> : <div className="empty-players"><Users size={22} /><p>Share the join code and your players will appear here.</p></div>}
              <button className="refresh-button" onClick={() => api(`/api/host/${hostEventId}`, { headers: { Authorization: `Bearer ${hostToken}` } }).then(setHostInfo).catch((reason) => setError(reason.message))}><Radio size={15} /> Refresh lobby</button>
            </div><p className="private-note">Lobby refresh is manual in this first iteration. Live updates arrive in a later milestone.</p>
          </>}
        </div>}
      </section>
      {view === 'create' && <footer className="page-footer"><span>BUILT FOR THE MOMENT BETWEEN “I KNOW THIS” AND “WAIT, WHAT?”</span><ArrowDown size={15} /></footer>}
      {view !== 'create' && <footer className="page-footer"><span>QUIZ AURA <i>·</i> GOOD QUESTIONS, BETTER COMPANY</span><span>POWERED BY CURIOSITY</span></footer>}
    </main>
  );
}
