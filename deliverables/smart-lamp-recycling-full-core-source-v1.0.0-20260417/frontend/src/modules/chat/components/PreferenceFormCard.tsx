import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import type {
  ChatCard,
  PreferenceFieldKey,
  PreferenceFormSubmission,
} from '../../../types/chat';

type PreferenceFormCardProps = {
  payload: Extract<ChatCard, { type: 'preference_form' }>['data'];
  onSubmit?: (payload: PreferenceFormSubmission) => void;
  submitting?: boolean;
};

type PreferenceState = Partial<Record<PreferenceFieldKey, string>>;
type PreferenceTextState = Partial<Record<PreferenceFieldKey, string>>;

export function PreferenceFormCard({
  payload,
  onSubmit,
  submitting,
}: PreferenceFormCardProps) {
  const initialValues = useMemo<PreferenceState>(() => {
    return payload.fields.reduce<PreferenceState>((acc, field) => {
      if (field.value) {
        acc[field.key] = field.value;
      } else if (field.options[0]) {
        acc[field.key] = field.options[0].value;
      }
      return acc;
    }, {});
  }, [payload.fields]);

  const initialTexts = useMemo<PreferenceTextState>(() => {
    return payload.fields.reduce<PreferenceTextState>((acc, field) => {
      const selectedValue = initialValues[field.key];
      const selectedOption = field.options.find((option) => option.value === selectedValue);
      acc[field.key] = selectedOption?.label || '';
      return acc;
    }, {});
  }, [initialValues, payload.fields]);

  const [values, setValues] = useState<PreferenceState>(initialValues);
  const [fieldTexts, setFieldTexts] = useState<PreferenceTextState>(initialTexts);
  const [note, setNote] = useState('');

  useEffect(() => {
    setValues(initialValues);
    setFieldTexts(initialTexts);
    setNote('');
  }, [initialTexts, initialValues, payload.session_id]);

  const isComplete = payload.fields.every((field) => Boolean(values[field.key]));

  function updateValue(field: PreferenceFieldKey, value: string, label: string) {
    if (submitting) {
      return;
    }
    setValues((prev) => ({
      ...prev,
      [field]: value,
    }));
    setFieldTexts((prev) => ({
      ...prev,
      [field]: label,
    }));
  }

  function handleFieldInput(
    fieldKey: PreferenceFieldKey,
    text: string,
    options: Array<{ value: string; label: string }>,
  ) {
    if (submitting) {
      return;
    }

    setFieldTexts((prev) => ({
      ...prev,
      [fieldKey]: text,
    }));

    const normalizedText = text.trim().toLowerCase();
    const matchedOption = options.find(
      (option) =>
        option.label.trim().toLowerCase() === normalizedText ||
        option.value.trim().toLowerCase() === normalizedText,
    );

    if (matchedOption) {
      setValues((prev) => ({
        ...prev,
        [fieldKey]: matchedOption.value,
      }));
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!onSubmit || submitting || !isComplete) {
      return;
    }

    const extraNotes = payload.fields
      .map((field) => {
        const typedText = fieldTexts[field.key]?.trim();
        const selectedOption = field.options.find(
          (option) => option.value === values[field.key],
        );

        if (!typedText || typedText === selectedOption?.label) {
          return '';
        }

        return `${field.label.replace(/[？?]/g, '')}: ${typedText}`;
      })
      .filter(Boolean);

    const mergedNote = [note.trim(), ...extraNotes].filter(Boolean).join('；');

    onSubmit({
      session_id: payload.session_id,
      install_type: values.install_type,
      space: values.space,
      budget_level: values.budget_level,
      note: mergedNote || undefined,
    });
  }

  return (
    <form className="biz-card preference-card" onSubmit={handleSubmit}>
      <div className="biz-card__head preference-card__head">
        <div>
          <strong>{payload.title}</strong>
          {payload.note ? <p>{payload.note}</p> : null}
        </div>
      </div>

      {payload.fields.map((field) => (
        <div key={field.key} className="preference-field">
          <span className="preference-field__label">{field.label}</span>
          <div className="preference-field__control">
            <input
              className="preference-field__input"
              type="text"
              value={fieldTexts[field.key] || ''}
              placeholder={`可直接输入${field.label.replace(/[？?]/g, '')}`}
              onChange={(event) =>
                handleFieldInput(field.key, event.target.value, field.options)
              }
              disabled={submitting}
            />
            <div
              className="preference-wheel preference-wheel--field"
              role="listbox"
              aria-label={`${field.label}滚轮选择`}
            >
              {field.options.map((option) => {
                const active = values[field.key] === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    className={`preference-wheel__item${active ? ' is-active' : ''}`}
                    aria-pressed={active}
                    onClick={() => updateValue(field.key, option.value, option.label)}
                  >
                    <strong>{option.label}</strong>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      ))}

      <div className="preference-note">
        <span className="preference-field__label">其他需求补充</span>
        <input
          className="preference-note__input"
          type="text"
          placeholder="例如：需要暖光、层高 2.8 米、希望简洁一些"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          disabled={submitting}
        />
      </div>

      <div className="biz-card__actions preference-card__actions">
        <button
          type="submit"
          className="primary-button primary-button--wide"
          disabled={!isComplete || submitting}
        >
          {submitting ? '提交中...' : payload.submit_label}
        </button>
      </div>
    </form>
  );
}
