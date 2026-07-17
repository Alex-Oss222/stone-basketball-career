export interface SegmentedTabOption<Value extends string> {
  readonly value: Value
  readonly label: string
  /** Marks a tab whose feature is not implemented yet. */
  readonly comingLater?: boolean
}

export interface SegmentedTabsProps<Value extends string> {
  readonly legend: string
  readonly name: string
  readonly value: Value
  readonly options: readonly SegmentedTabOption<Value>[]
  readonly onChange: (value: Value) => void
}

/**
 * An accessible radio-group tab row shared by the schedule surfaces. Selection
 * is presentation-only; the caller renders whatever content a value maps to,
 * including a coming-later placeholder for tabs without data yet.
 */
export function SegmentedTabs<Value extends string>({
  legend,
  name,
  value,
  options,
  onChange,
}: SegmentedTabsProps<Value>) {
  return (
    <fieldset className="segmented-tabs">
      <legend>{legend}</legend>
      {options.map((option) => (
        <label
          key={option.value}
          className={
            value === option.value
              ? 'segmented-tab is-active'
              : 'segmented-tab'
          }
        >
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          <span>{option.label}</span>
          {option.comingLater === true && (
            <span className="segmented-tab-soon">Soon</span>
          )}
        </label>
      ))}
    </fieldset>
  )
}
