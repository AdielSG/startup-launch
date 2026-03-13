const YC_BATCHES = [
  'W16','S16','W17','S17','W18','S18','W19','S19',
  'W20','S20','W21','S21','W22','S22','W23','S23',
  'W24','S24','W25','S25',
]

const SELECT_CLS =
  'bg-white border border-gray-200 text-gray-700 text-sm rounded-lg px-3 py-1.5 ' +
  'outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'

export default function FilterBar({ batch, onBatchChange, perf, onPerfChange }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
        Filter
      </span>

      <select
        value={batch}
        onChange={e => onBatchChange(e.target.value)}
        className={SELECT_CLS}
      >
        <option value="">All Batches</option>
        <option value="assessment">★ Assessment List</option>
        {YC_BATCHES.map(b => (
          <option key={b} value={b}>{b}</option>
        ))}
      </select>

      <select
        value={perf}
        onChange={e => onPerfChange(e.target.value)}
        className={SELECT_CLS}
      >
        <option value="">All Performance</option>
        <option value="poor">Poor performers</option>
        <option value="strong">Strong performers</option>
      </select>
    </div>
  )
}
