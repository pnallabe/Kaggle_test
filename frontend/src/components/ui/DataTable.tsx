import { FC, useMemo } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { cn } from '@utils/cn';

interface Column<T> {
  key: keyof T;
  label: string;
  sortable?: boolean;
  width?: string;
  render?: (value: unknown, row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  className?: string;
  rowClassName?: string;
}

const DataTable = <T extends Record<string, unknown>>({
  data,
  columns,
  className,
  rowClassName,
}: DataTableProps<T>) => {
  const [sortBy, setSortBy] = useMemo(() => {
    const state = { key: null as keyof T | null, order: 'asc' as 'asc' | 'desc' };
    return [
      state,
      (key: keyof T) => {
        if (state.key === key) {
          state.order = state.order === 'asc' ? 'desc' : 'asc';
        } else {
          state.key = key;
          state.order = 'asc';
        }
      },
    ];
  }, []);

  const sortedData = useMemo(() => {
    if (!sortBy.key) return data;

    return [...data].sort((a, b) => {
      const aVal = a[sortBy.key as keyof T];
      const bVal = b[sortBy.key as keyof T];

      if (aVal < bVal) return sortBy.order === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortBy.order === 'asc' ? 1 : -1;
      return 0;
    });
  }, [data, sortBy.key, sortBy.order]);

  return (
    <div className={cn('overflow-x-auto rounded-lg border border-border', className)}>
      <table className="w-full text-sm">
        <thead className="bg-muted/50 border-b border-border">
          <tr>
            {columns.map((col) => (
              <th
                key={String(col.key)}
                style={{ width: col.width }}
                className="px-4 py-3 text-left font-medium text-foreground"
              >
                <div className="flex items-center gap-2">
                  {col.label}
                  {col.sortable && (
                    <button
                      onClick={() => (setSortBy as any)(col.key)}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {sortBy.key === col.key ? (
                        sortBy.order === 'asc' ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )
                      ) : (
                        <ChevronUp className="h-4 w-4 opacity-30" />
                      )}
                    </button>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, idx) => (
            <tr
              key={idx}
              className={cn(
                'border-b border-border hover:bg-muted/50 transition-colors',
                rowClassName
              )}
            >
              {columns.map((col) => (
                <td
                  key={String(col.key)}
                  style={{ width: col.width }}
                  className="px-4 py-3 text-foreground"
                >
                  {col.render
                    ? col.render(row[col.key], row)
                    : String(row[col.key] || '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {sortedData.length === 0 && (
        <div className="py-8 text-center text-muted-foreground">
          No data available
        </div>
      )}
    </div>
  );
};

export default DataTable;
