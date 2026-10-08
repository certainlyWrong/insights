const queue = [];
let timer;

function scheduleNext(delay) {
  if (timer || !queue.length) return;
  timer = window.setTimeout(() => {
    timer = undefined;
    const task = queue.shift();
    try {
      task?.run();
    } catch (error) {
      console.error("Falha ao inicializar um gráfico:", error);
    } finally {
      scheduleNext(32);
    }
  }, delay);
}

export function enqueueChartInit(run) {
  const task = { run };
  queue.push(task);
  scheduleNext(0);
  return () => {
    const index = queue.indexOf(task);
    if (index >= 0) queue.splice(index, 1);
    if (!queue.length && timer) {
      window.clearTimeout(timer);
      timer = undefined;
    }
  };
}
