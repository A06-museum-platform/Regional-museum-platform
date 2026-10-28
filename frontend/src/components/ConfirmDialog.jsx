import { useState } from 'react';
import Modal from './Modal';
import Button from './Button';

/**
 * Confirmation for a destructive action.
 *
 * Three rules, all of which come out of the wireframe review:
 *   1. Say what will actually happen, in plain words.
 *   2. The destructive button is never the one focus lands on.
 *   3. If the action is logged, collect the reason here, not afterwards.
 */
export default function ConfirmDialog({
  title,
  body,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  reasonLabel,
  reasonRequired = false,
  onConfirm,
  onCancel,
  busy = false,
}) {
  const [reason, setReason] = useState('');
  const blocked = reasonRequired && !reason.trim();

  return (
    <Modal
      narrow
      title={title}
      onClose={onCancel}
      footer={
        <>
          <Button variant="ghost" onClick={onCancel}>{cancelLabel}</Button>
          <Button
            variant="danger"
            disabled={blocked || busy}
            onClick={() => onConfirm(reason.trim())}
          >
            {busy ? 'Working…' : confirmLabel}
          </Button>
        </>
      }
    >
      <p style={{ color: 'var(--c-muted)', fontSize: 14 }}>{body}</p>

      {reasonLabel && (
        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor="confirm-reason">
            {reasonLabel}
            {!reasonRequired && (
              <span style={{ fontWeight: 400, color: 'var(--c-muted)' }}> (optional)</span>
            )}
          </label>
          <input
            id="confirm-reason"
            className="control"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </div>
      )}
    </Modal>
  );
}
