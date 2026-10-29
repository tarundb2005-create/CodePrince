import { type FormEvent, useState } from 'react';
import { AlertTriangle, KeyRound, X } from 'lucide-react';

export const adminApi = async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
  const response = await fetch(`/api${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    let message = response.statusText;
    if (typeof body.detail === 'string') {
      message = body.detail;
    } else if (Array.isArray(body.detail)) {
      message = body.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join('; ');
    } else if (body.detail && typeof body.detail === 'object') {
      message = body.detail.msg || body.detail.message || JSON.stringify(body.detail);
    }
    throw Error(message);
  }
  return (response.status === 204 ? null : response.json()) as Promise<T>;
};

type ResetPasswordDialogProps = {
  title: string;
  subject: string;
  endpoint: string;
  close: () => void;
  onDone: () => void;
};

export function ResetPasswordDialog({ title, subject, endpoint, close, onDone }: ResetPasswordDialogProps) {
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Use at least 8 characters.');
      return;
    }
    if (password !== confirmation) {
      setError('The passwords do not match.');
      return;
    }
    setPending(true);
    try {
      await adminApi(endpoint, { method: 'POST', body: JSON.stringify({ password }) });
      onDone();
      close();
    } catch (exception) {
      setError((exception as Error).message);
    } finally {
      setPending(false);
    }
  };

  return <div className="admin-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
    <form className="admin-modal admin-modal-sm admin-confirm-modal" onSubmit={submit}>
      <header className="admin-modal-header">
        <div className="admin-modal-header-content">
          <span className="admin-modal-eyebrow">ACCOUNT SECURITY</span>
          <h2>{title}</h2>
          <p>{subject}</p>
        </div>
        <button type="button" className="admin-modal-close" onClick={close} aria-label="Close"><X/></button>
      </header>
      <div className="admin-modal-body">
        <div className="admin-modal-form-grid">
          <label>New password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} required autoComplete="new-password" placeholder="At least 8 characters"/></label>
          <label>Confirm password<input type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} minLength={8} required autoComplete="new-password" placeholder="Repeat the new password"/></label>
        </div>
        <p className="admin-modal-form-note"><KeyRound/> All active sessions for this account will be signed out.</p>
        {error && <p className="admin-modal-form-error">{error}</p>}
      </div>
      <footer className="admin-modal-footer">
        <button type="button" className="admin-btn admin-btn-secondary" onClick={close}>Cancel</button>
        <button type="submit" className="admin-btn admin-btn-primary" disabled={pending}>{pending ? 'Resetting…' : 'Reset password'}</button>
      </footer>
    </form>
  </div>;
}

type ConfirmDialogProps = {
  title: string;
  description: string;
  confirmLabel: string;
  pending?: boolean;
  error?: string;
  close: () => void;
  onConfirm: () => void;
};

export function ConfirmDialog({ title, description, confirmLabel, pending = false, error = '', close, onConfirm }: ConfirmDialogProps) {
  return <div className="admin-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
    <section className="admin-modal admin-modal-sm admin-confirm-modal">
      <header className="admin-modal-header">
        <div className="admin-modal-header-content">
          <span className="admin-confirm-icon"><AlertTriangle/></span>
          <span className="admin-modal-eyebrow">PLEASE CONFIRM</span>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <button type="button" className="admin-modal-close" onClick={close} aria-label="Close"><X/></button>
      </header>
      <div className="admin-modal-body">
        {error && <p className="admin-modal-form-error">{error}</p>}
      </div>
      <footer className="admin-modal-footer">
        <button type="button" className="admin-btn admin-btn-secondary" onClick={close}>Cancel</button>
        <button type="button" className="admin-btn admin-btn-danger" onClick={onConfirm} disabled={pending}>{pending ? 'Working…' : confirmLabel}</button>
      </footer>
    </section>
  </div>;
}
