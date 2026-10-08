const compactMonths = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export function formatPeriodLabel(value) {
  const text = String(value);
  const date = text.match(/^(\d{4})-(\d{2})(?:-\d{2})?$/);
  if (date) return `${compactMonths[Number(date[2]) - 1]}/${date[1].slice(-2)}`;
  const quarter = text.match(/^(\d{4})-T([1-4])$/);
  if (quarter) return `T${quarter[2]}/${quarter[1].slice(-2)}`;
  const semester = text.match(/^(\d{4})-S([12])$/);
  if (semester) return `S${semester[2]}/${semester[1].slice(-2)}`;
  return text;
}

function wrapCategoryLabel(value, maxLineLength = 13) {
  const words = String(value).split(/\s+/).filter(Boolean);
  if (words.length < 2) return String(value);
  const lines = [];
  let line = "";
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (line && next.length > maxLineLength) {
      lines.push(line);
      line = word;
    } else line = next;
  }
  if (line) lines.push(line);
  return lines.join("\n");
}

function normalizeAxes(value, isX = false) {
  if (!value) return value;
  const axes = Array.isArray(value) ? value : [value];
  const normalized = axes.map((axis) => {
    const axisLabel = { ...axis.axisLabel, fontSize: 12 };
    if (isX) {
      axisLabel.hideOverlap = true;
      axisLabel.rotate = 0;
      axisLabel.margin = 10;
      if (axis.type === "time") {
        // ECharts' time scale chooses year, quarter, or month ticks from the zoom extent.
        delete axisLabel.interval;
        delete axisLabel.formatter;
      } else if (axis.type === "category" && Array.isArray(axis.data)) {
        const temporal = axis.data.every((period) => /^(?:\d{4}|\d{4}-(?:\d{2}|T[1-4]|S[12])(?:-\d{2})?)$/.test(String(period)));
        if (temporal) {
          axisLabel.interval = "auto";
          axisLabel.formatter = formatPeriodLabel;
        } else if (axis.data.some((label) => String(label).length > 12)) {
          axisLabel.interval = "auto";
          axisLabel.lineHeight = 15;
          axisLabel.formatter = (label) => wrapCategoryLabel(label);
        }
      }
    } else axisLabel.hideOverlap = true;
    return {
      ...axis,
      axisLabel,
      nameTextStyle: { ...axis.nameTextStyle, fontSize: 13 },
    };
  });
  return Array.isArray(value) ? normalized : normalized[0];
}

/** Keep temporal axes native so ECharts can adapt tick spacing to the visible range. */
export function readableChartOption(option) {
  const xAxis = Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis;
  if (!xAxis) return option;

  const categories = xAxis.type === "category" && Array.isArray(xAxis.data) ? xAxis.data : [];
  const temporalCategory = categories.length > 0
    && categories.every((period) => /^(?:\d{4}|\d{4}-(?:\d{2}|T[1-4]|S[12])(?:-\d{2})?)$/.test(String(period)));
  const timePoints = (option.series || []).reduce((count, series) => count + (Array.isArray(series.data) ? series.data.length : 0), 0);
  const needsNavigation = (xAxis.type === "time" && timePoints > 12) || (temporalCategory && categories.length > 12);
  const hasLongCategories = categories.some((label) => String(label).length > 12);
  const legendValues = Array.isArray(option.legend) ? option.legend : option.legend ? [option.legend] : [];
  const legend = legendValues.map((item) => {
    const next = {
      ...item,
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 16,
      textStyle: { ...item.textStyle, fontSize: 12 },
    };
    if (needsNavigation) {
      delete next.bottom;
      next.type = "scroll";
      next.top = 4;
      next.height = 26;
      next.pageIconSize = 12;
    }
    return next;
  });
  const chartColors = option.color || [];
  const zoomAccent = chartColors[1] || chartColors[0] || "#188984";
  const zoomAccentFill = /^#[\da-f]{6}$/i.test(zoomAccent) ? `${zoomAccent}3d` : zoomAccent;
  const baseGrid = option.grid || {};
  let grid = baseGrid;
  if (needsNavigation) {
    grid = Array.isArray(baseGrid)
      ? baseGrid.map((item) => ({ ...item, top: Math.max(Number(item.top) || 0, 46), bottom: Math.max(Number(item.bottom) || 0, 76) }))
      : { ...baseGrid, top: Math.max(Number(baseGrid.top) || 0, 46), bottom: Math.max(Number(baseGrid.bottom) || 0, 76) };
  } else if (hasLongCategories) {
    grid = Array.isArray(baseGrid)
      ? baseGrid.map((item) => ({ ...item, bottom: Math.max(Number(item.bottom) || 0, 88) }))
      : { ...baseGrid, bottom: Math.max(Number(baseGrid.bottom) || 0, 88) };
  }

  const shared = {
    ...option,
    grid,
    xAxis: normalizeAxes(option.xAxis, true),
    yAxis: normalizeAxes(option.yAxis),
    legend,
    tooltip: option.tooltip ? {
      ...option.tooltip,
      textStyle: { ...option.tooltip.textStyle, fontSize: 14 },
      padding: [10, 12],
    } : option.tooltip,
  };
  if (!needsNavigation) return shared;

  // Keep the full series visible on first render; users can zoom in or pan as needed.
  return {
    ...shared,
    dataZoom: [
      { type: "inside", xAxisIndex: 0, start: 0, end: 100, filterMode: "filter", zoomOnMouseWheel: true, moveOnMouseMove: true },
      {
        type: "slider", xAxisIndex: 0, start: 0, end: 100, bottom: 8, height: 18,
        showDetail: false, brushSelect: false, borderColor: "transparent",
        backgroundColor: "rgba(120, 112, 104, 0.12)", fillerColor: zoomAccentFill,
        handleStyle: { color: zoomAccent, borderColor: zoomAccent },
        moveHandleStyle: { color: zoomAccent },
      },
    ],
  };
}
