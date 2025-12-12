import { useEffect, useState } from 'react';
import { classifyNodeCandidate, createNode, updateNode, suggestNodeSector } from '../api/client';
import { useRefreshStore } from '../store/dataRefreshStore';
import { useUiStore } from '../store/uiStore';
import { NODE_TYPES } from '../types';
import type {
  NodeClassificationResponsePayload,
  NodeRequestPayload,
  NodeType,
  NodeSectorSuggestionResponsePayload,
} from '../types';
import './NodeModal.css';

const defaultValues: Record<NodeType, Partial<NodeRequestPayload>> = {
  PERSON: {
    relationshipStrength: 3,
    sector: '',
  },
  GOAL: {
    priority: 3,
  },
  PROJECT: {
    status: 'TODO',
  },
  VISION: {},
};

const typeOrder: NodeType[] = [NODE_TYPES.VISION, NODE_TYPES.GOAL, NODE_TYPES.PROJECT, NODE_TYPES.PERSON];
const typeText: Record<NodeType, string> = {
  PERSON: 'Kişi',
  GOAL: 'Hedef',
  PROJECT: 'Proje',
  VISION: 'Vizyon',
};

const sectorInputId = 'node-sector-input';

function parseTags(value: string): string[] | undefined {
  const tokens = value
    .split(',')
    .map((token) => token.trim())
    .filter((token) => token.length > 0);
  return tokens.length ? tokens : undefined;
}

export function NodeModal() {
  const modal = useUiStore((state) => state.nodeModal);
  const closeModal = useUiStore((state) => state.closeModal);
  const triggerGraphRefresh = useRefreshStore((state) => state.triggerGraphRefresh);
  const triggerVisionRefresh = useRefreshStore((state) => state.triggerVisionRefresh);
  const [form, setForm] = useState<NodeRequestPayload>({
    type: NODE_TYPES.PERSON,
    name: '',
    description: '',
    sector: '',
    relationshipStrength: 3,
    notes: '',
  });
  const [tagInput, setTagInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [classification, setClassification] = useState<NodeClassificationResponsePayload | null>(null);
  const [classificationLoading, setClassificationLoading] = useState(false);
  const [classificationError, setClassificationError] = useState<string | null>(null);
  const [sectorSuggestion, setSectorSuggestion] = useState<NodeSectorSuggestionResponsePayload | null>(null);
  const [sectorSuggestionLoading, setSectorSuggestionLoading] = useState(false);
  const [sectorSuggestionError, setSectorSuggestionError] = useState<string | null>(null);

  useEffect(() => {
    if (!modal) {
      return;
    }
    if (modal.mode === 'edit') {
      const node = modal.node;
      setForm({
        type: node.type,
        name: node.name ?? '',
        description: node.description ?? '',
        sector: node.sector ?? '',
        relationshipStrength: node.relationshipStrength ?? undefined,
        company: node.company ?? '',
        role: node.role ?? '',
        linkedinUrl: node.linkedinUrl ?? '',
        priority: node.priority ?? undefined,
        dueDate: node.dueDate ?? undefined,
        startDate: node.startDate ?? undefined,
        endDate: node.endDate ?? undefined,
        status: node.status ?? undefined,
        notes: node.notes ?? '',
        tags: node.tags ?? undefined,
        properties: node.properties ?? undefined,
      });
      setTagInput(node.tags?.join(', ') ?? '');
    } else {
      setForm({
        type: modal.nodeType,
        name: '',
        description: '',
        sector: '',
        relationshipStrength: defaultValues[modal.nodeType].relationshipStrength,
        company: '',
        role: '',
        linkedinUrl: '',
        priority: defaultValues[modal.nodeType].priority,
        dueDate: undefined,
        startDate: undefined,
        endDate: undefined,
        status: defaultValues[modal.nodeType].status,
        notes: '',
        tags: undefined,
        properties: undefined,
      });
      setTagInput('');
    }
    setError(null);
    setClassification(null);
    setClassificationError(null);
    setClassificationLoading(false);
    setSectorSuggestion(null);
    setSectorSuggestionError(null);
    setSectorSuggestionLoading(false);
  }, [modal]);

  if (!modal) {
    return null;
  }

  const handleChange = (field: keyof NodeRequestPayload, value: unknown) => {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const applyTypeDefaults = (type: NodeType, previous: NodeRequestPayload): NodeRequestPayload => {
    const next: NodeRequestPayload = {
      ...previous,
      type,
    };
    if (type !== NODE_TYPES.PERSON) {
      next.relationshipStrength = undefined;
    }
    if (type !== NODE_TYPES.GOAL) {
      next.priority = undefined;
      next.dueDate = undefined;
    }
    if (type !== NODE_TYPES.PROJECT) {
      next.status = undefined;
      next.startDate = undefined;
      next.endDate = undefined;
    }
    return {
      ...next,
      ...defaultValues[type],
    };
  };

  const handleTypeChange = (type: NodeType) => {
    setForm((prev) => applyTypeDefaults(type, prev));
  };

  const handleClassification = async () => {
    if (!form.name?.trim()) {
      setClassificationError('Önce isim alanını doldurun.');
      return;
    }
    setClassificationLoading(true);
    setClassificationError(null);
    try {
      const response = await classifyNodeCandidate({
        name: form.name ?? '',
        description: form.description,
        notes: form.notes,
        tags: form.tags,
        sector: form.sector,
        priority: form.priority,
        status: form.status,
        dueDate: form.dueDate,
        startDate: form.startDate,
        endDate: form.endDate,
      });
      setClassification(response);
    } catch (err) {
      console.error('Classification failed', err);
      setClassification(null);
      setClassificationError('Tasnif önerisi getirilemedi.');
    } finally {
      setClassificationLoading(false);
    }
  };

  const applyClassification = () => {
    if (classification) {
      handleTypeChange(classification.suggestedType);
    }
  };

  const handleSectorSuggestion = async () => {
    const hasName = Boolean(form.name?.trim());
    const hasDescription = Boolean(form.description?.trim());
    const hasNotes = Boolean(form.notes?.trim());
    const hasTags = Boolean(form.tags?.length);
    if (!hasName && !hasDescription && !hasNotes && !hasTags) {
      setSectorSuggestionError('Önce isim, açıklama, not veya etiket girin.');
      return;
    }
    setSectorSuggestionLoading(true);
    setSectorSuggestionError(null);
    try {
      const response = await suggestNodeSector({
        name: form.name ?? '',
        description: form.description,
        notes: form.notes,
        tags: form.tags,
      });
      setSectorSuggestion(response);
      if ((!form.sector || !form.sector.trim()) && response.sector) {
        handleChange('sector', response.sector);
      }
    } catch (err) {
      console.error('Sector suggestion failed', err);
      setSectorSuggestion(null);
      setSectorSuggestionError('Sektör önerisi getirilemedi.');
    } finally {
      setSectorSuggestionLoading(false);
    }
  };

  const applySectorSuggestion = () => {
    if (sectorSuggestion?.sector) {
      handleChange('sector', sectorSuggestion.sector);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (modal.mode === 'create') {
        await createNode(form);
      } else {
        await updateNode(modal.node.id, form);
      }
      triggerGraphRefresh();
      triggerVisionRefresh();
      closeModal();
    } catch (err) {
      console.error('Node mutation failed', err);
      setError('İşlem başarısız oldu. Lütfen tekrar deneyin.');
    } finally {
      setLoading(false);
    }
  };

  const label = modal.mode === 'create' ? 'Yeni' : 'Düzenle';
  const typeLabel = form.type;

  return (
    <div className="modal-overlay">
      <form className="modal-card" onSubmit={handleSubmit}>
        <div className="modal-header">
          <h3>
            {label} {typeText[typeLabel]}
          </h3>
          <button type="button" className="ghost-button" onClick={closeModal}>
            Kapat
          </button>
        </div>
        <div className="type-switcher">
          {typeOrder.map((nodeType) => (
            <button
              key={nodeType}
              type="button"
              className={`type-chip ${form.type === nodeType ? 'active' : ''}`}
              onClick={() => handleTypeChange(nodeType)}
            >
              {typeText[nodeType]}
            </button>
          ))}
        </div>
        <div className="classification-card">
          <div>
            <strong>Otomatik Tasnif</strong>
            {classification ? (
              <p>
                {typeText[classification.suggestedType]}  {(classification.confidence * 100).toFixed(0)}%
              </p>
            ) : (
              <p className="muted">İsim ve açıklama girdikten sonra öneri alabilirsiniz.</p>
            )}
          </div>
          <div className="classification-actions">
            <button type="button" className="ghost-button" onClick={handleClassification} disabled={classificationLoading}>
              {classificationLoading ? 'Analiz ediliyor...' : 'Tip Öner'}
            </button>
            {classification && classification.suggestedType !== form.type && (
              <button type="button" className="ghost-button" onClick={applyClassification}>
                Öneriyi Uygula
              </button>
            )}
          </div>
          {classificationError && <small className="error-text">{classificationError}</small>}
          {classification?.matchedSignals && classification.matchedSignals.length > 0 && (
            <ul className="classification-signals">
              {classification.matchedSignals.map((signal) => (
                <li key={signal}>{signal}</li>
              ))}
            </ul>
          )}
        </div>
        <label>
          İsim
          <input value={form.name ?? ''} onChange={(event) => handleChange('name', event.target.value)} required />
        </label>
        <label>
          Açıklama
          <textarea
            value={form.description ?? ''}
            onChange={(event) => handleChange('description', event.target.value)}
            rows={3}
          />
        </label>
        <div className="sector-field">
          <div className="label-row">
            <label htmlFor={sectorInputId}>Sektör</label>
            <div className="sector-actions">
              <button
                type="button"
                className="ghost-button"
                onClick={handleSectorSuggestion}
                disabled={sectorSuggestionLoading}
              >
                {sectorSuggestionLoading ? 'Analiz ediliyor...' : 'Sektör Öner'}
              </button>
              {sectorSuggestion && (
                <button type="button" className="ghost-button" onClick={applySectorSuggestion}>
                  Sektörü Uygula
                </button>
              )}
            </div>
          </div>
          <input
            id={sectorInputId}
            value={form.sector ?? ''}
            onChange={(event) => handleChange('sector', event.target.value)}
          />
          {sectorSuggestion && (
            <div className="sector-suggestion">
              <div className="sector-suggestion-summary">
                <strong>{sectorSuggestion.sector}</strong>
                <span className="confidence">Güven {(sectorSuggestion.confidence * 100).toFixed(0)}%</span>
              </div>
              {sectorSuggestion.matchedKeywords && sectorSuggestion.matchedKeywords.length > 0 && (
                <small>Anahtar Kelimeler: {sectorSuggestion.matchedKeywords.join(', ')}</small>
              )}
              {sectorSuggestion.rationale && <small>{sectorSuggestion.rationale}</small>}
            </div>
          )}
          {sectorSuggestionError && <small className="error-text">{sectorSuggestionError}</small>}
        </div>
        <label>
          Etiketler
          <input
            value={tagInput}
            onChange={(event) => {
              const value = event.target.value;
              setTagInput(value);
              handleChange('tags', parseTags(value));
            }}
            placeholder="mentor, yatirimci..."
          />
        </label>
        {typeLabel === NODE_TYPES.PERSON && (
          <label>
            İlişki Gücü (0-5)
            <div className="strength-selector">
              {[0, 1, 2, 3, 4, 5].map((val) => (
                <button
                  key={val}
                  type="button"
                  className={`strength-btn ${form.relationshipStrength === val ? 'active' : ''}`}
                  onClick={() => handleChange('relationshipStrength', val)}
                >
                  {val}
                </button>
              ))}
            </div>
          </label>
        )}
        {typeLabel === NODE_TYPES.GOAL && (
          <label>
            Öncelik (1-5)
            <input
              type="number"
              min={1}
              max={5}
              value={form.priority ?? ''}
              onChange={(event) => handleChange('priority', event.target.value === '' ? undefined : Number(event.target.value))}
            />
          </label>
        )}
        {typeLabel === NODE_TYPES.GOAL && (
          <label>
            Bitiş Tarihi
            <input
              type="date"
              value={form.dueDate ?? ''}
              onChange={(event) => handleChange('dueDate', event.target.value || undefined)}
            />
          </label>
        )}
        {typeLabel === NODE_TYPES.PROJECT && (
          <>
            <label>
              Başlangıç Tarihi
              <input
                type="date"
                value={form.startDate ?? ''}
                onChange={(event) => handleChange('startDate', event.target.value || undefined)}
              />
            </label>
            <label>
              Bitiş Tarihi
              <input
                type="date"
                value={form.endDate ?? ''}
                onChange={(event) => handleChange('endDate', event.target.value || undefined)}
              />
            </label>
            <label>
              Durum
              <select value={form.status ?? 'TODO'} onChange={(event) => handleChange('status', event.target.value)}>
                <option value="TODO">Yapılacak</option>
                <option value="DOING">Devam Ediyor</option>
                <option value="DONE">Tamamlandı</option>
              </select>
            </label>
          </>
        )}
        <label>
          Notlar
          <textarea value={form.notes ?? ''} onChange={(event) => handleChange('notes', event.target.value)} rows={2} />
        </label>
        {error && <p className="error-text">{error}</p>}
        <button className="primary-button block" type="submit" disabled={loading}>
          {loading ? 'Kaydediliyor...' : 'Kaydet'}
        </button>
      </form>
    </div>
  );
}
