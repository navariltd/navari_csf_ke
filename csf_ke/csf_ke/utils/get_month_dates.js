/**
 * Returns the last date of the month for the given input date.
 *
 * @param {string|Date} inputDate - The date from which to calculate the last day of the month.
 *                                  Can be a Date object or a date string.
 * @returns {Date} The last date of the month for the provided input date.
 */
function get_last_month_date(inputDate) {
  const date = new Date(inputDate);

  // if the input month is December, set the month
  //  to January of the next year
  if (date.getMonth() === 11) {
    date.setFullYear(date.getFullYear() + 1);
    date.setMonth(0); // January
  } else {
    // otherwise, just set the month to the next month
    date.setMonth(date.getMonth() + 1);
  }
  // set the date to the first day of the month
  date.setDate(1);

  // subtract one day to get the last day of the current month
  date.setDate(date.getDate() - 1);

  console.log("Last month date:", date);

  return date;
}

/**
 * Returns a Date object set to the first day of the month for the given input date.
 *
 * @param {string|Date} inputDate - The input date as a string or Date object.
 * @returns {Date} A Date object representing the first day of the month.
 */
function get_first_month_date(inputDate) {
  const date = new Date(inputDate);
  // set the date to the first day of the month
  date.setDate(1);

  console.log("First month date:", date);
  return date;
}
