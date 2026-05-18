(function () {
  function initDatePickers() {
    if (typeof flatpickr === "undefined") return;

    document.querySelectorAll(".date-picker:not(.flatpickr-input)").forEach((el) => {
      flatpickr(el, {
        dateFormat: "d-m-Y",
        altInput: false,
        allowInput: true,
        disableMobile: false,
        locale: {
          firstDayOfWeek: 1,
        },
        onReady: function (_selected, _str, instance) {
          if (instance.calendarContainer) {
            instance.calendarContainer.classList.add("tms-flatpickr");
          }
        },
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDatePickers);
  } else {
    initDatePickers();
  }
})();
