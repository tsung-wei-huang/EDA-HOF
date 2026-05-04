// Acceptance rate data for DAC and ICCAD
// Sources: openaccept.org, ACM DL, conference announcements
// DAC: starts from 2018 (pre-2018 data incomplete)
// ICCAD: 2013–2025 (complete from openaccept.org)

const AC_RATE_DATA = {
  dac: [
    { year: 2018, submitted: 691,  accepted: 168, rate: 24.31 },
    { year: 2019, submitted: 815,  accepted: 202, rate: 24.79 },
    { year: 2020, submitted: 984,  accepted: 228, rate: 23.17 },
    { year: 2021, submitted: 914,  accepted: 215, rate: 23.52 },
    { year: 2022, submitted: 987,  accepted: 223, rate: 22.59 },
    { year: 2023, submitted: 1156, accepted: 263, rate: 22.75 },
    { year: 2024, submitted: 1545, accepted: 337, rate: 21.81 },
    { year: 2025, submitted: 1862, accepted: 420, rate: 22.56 },
  ],
  iccad: [
    { year: 2013, submitted: 354,  accepted: 92,  rate: 25.99 },
    { year: 2014, submitted: 304,  accepted: 77,  rate: 25.33 },
    { year: 2015, submitted: 382,  accepted: 94,  rate: 24.61 },
    { year: 2016, submitted: 409,  accepted: 97,  rate: 23.72 },
    { year: 2017, submitted: 399,  accepted: 105, rate: 26.32 },
    { year: 2018, submitted: 400,  accepted: 98,  rate: 24.50 },
    { year: 2019, submitted: 394,  accepted: 94,  rate: 23.86 },
    { year: 2020, submitted: 470,  accepted: 127, rate: 27.02 },
    { year: 2021, submitted: 514,  accepted: 121, rate: 23.54 },
    { year: 2022, submitted: 595,  accepted: 132, rate: 22.18 },
    { year: 2023, submitted: 750,  accepted: 172, rate: 22.93 },
    { year: 2024, submitted: 802,  accepted: 195, rate: 24.31 },
    { year: 2025, submitted: 1078, accepted: 266, rate: 24.68 },
  ],
};
