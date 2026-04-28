type StrategyConfigFormProps = {
  onSubmit: () => void;
  isSubmitting: boolean;
};

export function StrategyConfigForm({ onSubmit, isSubmitting }: StrategyConfigFormProps) {
  return (
    <section aria-label="run-form">
      <h1>选股工作台</h1>
      <label>
        K 线天数
        <input defaultValue={120} name="kline_days" type="number" />
      </label>
      <button disabled={isSubmitting} onClick={onSubmit} type="button">
        {isSubmitting ? "运行中" : "开始选股"}
      </button>
    </section>
  );
}
