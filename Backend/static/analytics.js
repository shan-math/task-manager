function initAnalytics(data) {
  const gridColor = "rgba(168, 168, 184, 0.15)";
  const textColor = "#a8a8b8";
  const font = { family: "'Inter', sans-serif", size: 13 };

  Chart.defaults.color = textColor;
  Chart.defaults.borderColor = gridColor;
  Chart.defaults.font = font;

  const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: textColor, font: { size: 14 }, padding: 16 },
      },
    },
  };

  const statusColors = ["#ff4466", "#ffb020", "#00e676"];
  const priorityColors = ["#ff4466", "#ffb020", "#00ffc8"];

  if (document.getElementById("statusChart") && data.status?.length) {
    new Chart(document.getElementById("statusChart"), {
      type: "doughnut",
      data: {
        labels: data.status.map((x) => x.status),
        datasets: [{
          data: data.status.map((x) => x.count),
          backgroundColor: statusColors,
          borderColor: "#0e0e14",
          borderWidth: 3,
        }],
      },
      options: {
        ...chartDefaults,
        cutout: "62%",
        plugins: { ...chartDefaults.plugins, legend: { position: "bottom" } },
      },
    });
  }

  if (document.getElementById("priorityChart") && data.priority?.length) {
    new Chart(document.getElementById("priorityChart"), {
      type: "bar",
      data: {
        labels: data.priority.map((x) => x.priority),
        datasets: [{
          label: "Tasks",
          data: data.priority.map((x) => x.count),
          backgroundColor: priorityColors,
          borderRadius: 6,
        }],
      },
      options: {
        ...chartDefaults,
        scales: {
          x: { grid: { display: false }, ticks: { color: textColor, font: { size: 14 } } },
          y: {
            beginAtZero: true,
            grid: { color: gridColor },
            ticks: { color: textColor, stepSize: 1 },
          },
        },
        plugins: { legend: { display: false } },
      },
    });
  }

  if (document.getElementById("completionChart")) {
    const labels = (data.completions || []).map((x) => {
      const d = x.day;
      return typeof d === "string" ? d.slice(5) : d;
    });
    const values = (data.completions || []).map((x) => x.completed);

    new Chart(document.getElementById("completionChart"), {
      type: "line",
      data: {
        labels: labels.length ? labels : ["No data"],
        datasets: [{
          label: "Completed",
          data: values.length ? values : [0],
          borderColor: "#00ffc8",
          backgroundColor: "rgba(0, 255, 200, 0.08)",
          fill: true,
          tension: 0.35,
          pointBackgroundColor: "#00ffc8",
          pointRadius: 4,
          pointHoverRadius: 6,
        }],
      },
      options: {
        ...chartDefaults,
        scales: {
          x: { grid: { color: gridColor }, ticks: { color: textColor, maxRotation: 45 } },
          y: {
            beginAtZero: true,
            grid: { color: gridColor },
            ticks: { color: textColor, stepSize: 1 },
          },
        },
        plugins: { legend: { display: false } },
      },
    });
  }
}
