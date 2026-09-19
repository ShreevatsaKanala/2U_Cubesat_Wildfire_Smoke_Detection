export interface DemoObservation {
  id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  altitudeKm: number;
  cameraAngle: number;
  smokeScore: number;
  confidence: string;
  priority: string;
  status: string;
  visualEvidence: string[];
  alternativeExplanations: string[];

  sentinelAvailable: boolean;
  sentinelSceneId: string | null;
  sentinelAcquisitionTime: string | null;
  sentinelCloudCover: number | null;
  sentinelProduct: string | null;
  sentinelTrueColorUrl: string | null;
  sentinelNdviUrl: string | null;
  sentinelFalseColorUrl: string | null;
}

export interface DemoDownlinkItem {
  observationId: string;
  priority: string;
  sizeBytes: number;
  status: string;
  bytesTransmitted: number;
  progressPct: number;
  assignedStation: string | null;
  band: string;
  rateBytesS: number;
}

export interface DemoGroundStation {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  isVisible: boolean;
  isLinked: boolean;
  elevationDeg: number;
  nextPassSeconds: number;
  status: string;
}

export interface DemoEvent {
  id: string;
  timestamp: string;
  type: string;
  severity: string;
  message: string;
}

export interface DemoState {
  missionElapsed: number;
  simSpeed: number;
  running: boolean;
  scenario: string;

  spacecraft: {
    id: string;
    mission: string;
    mode: string;
    latitude: number;
    longitude: number;
    altitudeKm: number;
    velocityKmS: number;
    headingDeg: number;
    orbitNumber: number;
  };

  attitude: {
    mode: string;
    rollDeg: number;
    pitchDeg: number;
    yawDeg: number;
    pointingErrorDeg: number;
  };

  power: {
    batterySoc: number;
    batteryVoltage: number;
    solarGenerationW: number;
    powerConsumptionW: number;
    powerBalanceW: number;
    eclipse: boolean;
    chargeState: string;
  };

  thermal: {
    obc: number;
    camera: number;
    battery: number;
    comms: number;
    structure: number;
  };

  health: {
    obc: string;
    camera: string;
    adcs: string;
    eps: string;
    thermal: string;
    comms: string;
    gps: string;
    ai: string;
  };

  observations: DemoObservation[];

  ai: {
    status: string;
    model: string;
    latestObservationId: string | null;
    smokeScore: number;
    confidence: string;
    latencyMs: number;
    visualEvidence: string[];
    alternativeExplanations: string[];
  };

  downlink: {
    queueSize: number;
    totalTransmitted: number;
    totalBytes: number;
    effectiveRateBytesS: number;
    currentBand: string;
    progress: {
      queuedCount: number;
      activeCount: number;
      completedCount: number;
      overallProgressPct: number;
    };
    items: DemoDownlinkItem[];
  };

  groundStations: DemoGroundStation[];

  events: DemoEvent[];

  hotspots: Array<{
    lat: number;
    lon: number;
    frp: number;
    confidence: string;
    id: string;
  }>;

  faults: {
    commLoss: boolean;
    lowBattery: boolean;
    thermalWarning: boolean;
  };
}

const ORBIT_RADIUS_KM = 6371 + 500;
const EARTH_ROTATION_DEG_PER_S = 360 / 86400;
const ORBIT_PERIOD_S = 5682;
const INCLINATION_DEG = 97.4;
const BASE_SOLAR_W = 8.4;
const BASE_CONSUMPTION_W = 2.6;
const BATTERY_CAPACITY_WH = 40;
const MAX_BATTERY_SOC = 100;

const GROUND_STATIONS: DemoGroundStation[] = [
  { id: "GS-001", name: "BOULDER", latitude: 40.015, longitude: -105.2705, isVisible: false, isLinked: false, elevationDeg: 0, nextPassSeconds: 2400, status: "STANDBY" },
  { id: "GS-002", name: "FAIRBANKS", latitude: 64.8378, longitude: -147.7164, isVisible: false, isLinked: false, elevationDeg: 0, nextPassSeconds: 4800, status: "STANDBY" },
  { id: "GS-003", name: "SVALBARD", latitude: 78.2232, longitude: 15.6267, isVisible: false, isLinked: false, elevationDeg: 0, nextPassSeconds: 3600, status: "STANDBY" },
  { id: "GS-004", name: "SINGAPORE", latitude: 1.3521, longitude: 103.8198, isVisible: false, isLinked: false, elevationDeg: 0, nextPassSeconds: 1200, status: "STANDBY" },
  { id: "GS-005", name: "PUNTA ARENAS", latitude: -53.1638, longitude: -70.9171, isVisible: false, isLinked: false, elevationDeg: 0, nextPassSeconds: 5400, status: "STANDBY" },
];

const VISUAL_EVIDENCE_POOL = [
  "Gray-white convective plume detected in NE quadrant",
  "Anomalous spectral signature consistent with biomass combustion",
  "Thermal hotspot detected in agricultural zone",
  "Elevated aerosol optical depth in 660nm band",
  "Plume morphology indicates active surface fire",
  "Multi-spectral analysis shows elevated CO concentrations",
  "Temporal pattern matches known wildfire progression",
  "Vegetation index degradation detected in surrounding area",
  "Hotspot cluster indicates multi-point ignition source",
  "Smoke column exhibits pyrocumulus characteristics",
];

const ALTERNATIVE_EXPLANATIONS = [
  "Industrial emissions from nearby processing facility",
  "Controlled agricultural burn in permitted zone",
  "Dust plume from construction activity",
  "Cloud formation misidentified as smoke",
  "Sensor noise from high solar zenith angle",
  "Cloud shadow creating false thermal signature",
  "Fog formation in river valley",
  "Power line spark with limited ground impact",
];

const SCENARIO_CONFIGS: Record<string, { observationInterval: number; smokeScoreRange: [number, number]; faultActive: string | null }> = {
  NORMAL: { observationInterval: 90, smokeScoreRange: [0.05, 0.45], faultActive: null },
  WILDFIRE: { observationInterval: 60, smokeScoreRange: [0.65, 0.98], faultActive: null },
  "HIGH PRIORITY": { observationInterval: 45, smokeScoreRange: [0.80, 0.99], faultActive: null },
  "LOW BATTERY": { observationInterval: 120, smokeScoreRange: [0.10, 0.30], faultActive: "lowBattery" },
  THERMAL: { observationInterval: 100, smokeScoreRange: [0.10, 0.35], faultActive: "thermalWarning" },
  "COMM LOSS": { observationInterval: 90, smokeScoreRange: [0.20, 0.50], faultActive: "commLoss" },
  RECOVERY: { observationInterval: 90, smokeScoreRange: [0.10, 0.40], faultActive: null },
};

function seededRandom(seed: number): number {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

export class DemoEngine {
  private state: DemoState;
  private tickCount: number = 0;
  private lastObservationTick: number = -200;
  private eventCounter: number = 0;
  private downlinkCounter: number = 0;
  private lastStationCheckTick: number = -100;
  private scenarioConfig = SCENARIO_CONFIGS["NORMAL"];

  constructor() {
    this.state = this.createInitialState();
  }

  private createInitialState(): DemoState {
    return {
      missionElapsed: 0,
      simSpeed: 1,
      running: false,
      scenario: "NORMAL",
      spacecraft: {
        id: "CUBESAT-2U-001",
        mission: "WILDFIRE DETECTION",
        mode: "CRUISE",
        latitude: 0,
        longitude: 0,
        altitudeKm: 501,
        velocityKmS: 7.61,
        headingDeg: 0,
        orbitNumber: 1,
      },
      attitude: {
        mode: "NADIR",
        rollDeg: 0.21,
        pitchDeg: -0.08,
        yawDeg: 91.42,
        pointingErrorDeg: 0.24,
      },
      power: {
        batterySoc: 82,
        batteryVoltage: 7.84,
        solarGenerationW: BASE_SOLAR_W,
        powerConsumptionW: BASE_CONSUMPTION_W,
        powerBalanceW: BASE_SOLAR_W - BASE_CONSUMPTION_W,
        eclipse: false,
        chargeState: "CHARGING",
      },
      thermal: {
        obc: 34.2,
        camera: 30.8,
        battery: 28.1,
        comms: 32.4,
        structure: 24.7,
      },
      health: {
        obc: "NOMINAL",
        camera: "ACTIVE",
        adcs: "NADIR",
        eps: "NOMINAL",
        thermal: "NOMINAL",
        comms: "LINKED",
        gps: "LOCKED",
        ai: "READY",
      },
      observations: [],
      ai: {
        status: "ONLINE",
        model: "VISION-DEMO",
        latestObservationId: null,
        smokeScore: 0,
        confidence: "HIGH",
        latencyMs: 1.84,
        visualEvidence: [],
        alternativeExplanations: [],
      },
      downlink: {
        queueSize: 0,
        totalTransmitted: 0,
        totalBytes: 0,
        effectiveRateBytesS: 0,
        currentBand: "X-BAND",
        progress: {
          queuedCount: 0,
          activeCount: 0,
          completedCount: 0,
          overallProgressPct: 0,
        },
        items: [],
      },
      groundStations: GROUND_STATIONS.map((gs) => ({ ...gs })),
      events: [],
      hotspots: [
        { id: "FIRE-001", lat: 37.75, lon: -122.42, frp: 45.2, confidence: "nominal" },
        { id: "FIRE-002", lat: 34.05, lon: -118.24, frp: 82.1, confidence: "high" },
        { id: "FIRE-003", lat: 36.17, lon: -115.14, frp: 28.7, confidence: "low" },
      ],
      faults: {
        commLoss: false,
        lowBattery: false,
        thermalWarning: false,
      },
    };
  }

  getState(): DemoState {
    return this.state;
  }

  start(): void {
    this.state.running = true;
    this.addEvent("MISSION", "INFO", "Mission simulation started");
  }

  pause(): void {
    this.state.running = false;
    this.addEvent("MISSION", "INFO", "Mission simulation paused");
  }

  reset(): void {
    this.state = this.createInitialState();
    this.tickCount = 0;
    this.lastObservationTick = -200;
    this.eventCounter = 0;
    this.downlinkCounter = 0;
    this.lastStationCheckTick = -100;
    this.scenarioConfig = SCENARIO_CONFIGS["NORMAL"];
  }

  setSpeed(speed: number): void {
    this.state.simSpeed = speed;
  }

  setScenario(scenario: string): void {
    this.state.scenario = scenario;
    this.scenarioConfig = SCENARIO_CONFIGS[scenario] || SCENARIO_CONFIGS["NORMAL"];
    if (scenario === "LOW BATTERY") {
      this.state.faults.lowBattery = true;
      this.state.power.batterySoc = 18;
    } else if (scenario === "THERMAL") {
      this.state.faults.thermalWarning = true;
      this.state.thermal.obc = 62;
    } else if (scenario === "COMM LOSS") {
      this.state.faults.commLoss = true;
      this.state.health.comms = "OFFLINE";
    } else if (scenario === "RECOVERY") {
      this.state.faults = { commLoss: false, lowBattery: false, thermalWarning: false };
      this.state.health.comms = "LINKED";
      this.state.health.obc = "NOMINAL";
      this.state.health.thermal = "NOMINAL";
    }
    this.addEvent("SCENARIO", "INFO", `Scenario changed to ${scenario}`);
  }

  injectFault(type: "commLoss" | "lowBattery" | "thermalWarning"): void {
    this.state.faults[type] = true;
    if (type === "lowBattery") {
      this.state.power.batterySoc = 15;
      this.state.health.eps = "WARNING";
    } else if (type === "thermalWarning") {
      this.state.thermal.obc = 68;
      this.state.health.thermal = "WARNING";
    } else if (type === "commLoss") {
      this.state.health.comms = "OFFLINE";
      this.state.health.ai = "OFFLINE";
    }
    this.addEvent("FAULT", "WARNING", `Fault injected: ${type}`);
  }

  clearFaults(): void {
    this.state.faults = { commLoss: false, lowBattery: false, thermalWarning: false };
    this.state.health.comms = "LINKED";
    this.state.health.ai = "READY";
    this.state.health.eps = "NOMINAL";
    this.state.health.thermal = "NOMINAL";
    this.state.power.batterySoc = 82;
    this.state.thermal.obc = 34.2;
    this.addEvent("FAULT", "INFO", "All faults cleared");
  }

  tick(): void {
    if (!this.state.running) return;
    this.tickCount++;

    const speed = this.state.simSpeed;
    const elapsedIncrement = speed;
    this.state.missionElapsed += elapsedIncrement;

    this.updateOrbit(elapsedIncrement);
    this.updateAttitude();
    this.updatePower(elapsedIncrement);
    this.updateThermal(elapsedIncrement);
    this.updateHealth();
    this.updateGroundStations();
    this.processDownlink(elapsedIncrement);
    this.checkObservations();
    this.updateHotspots();
    this.pruneEvents();
  }

  private updateOrbit(elapsed: number): void {
    const t = this.state.missionElapsed;
    const period = ORBIT_PERIOD_S;
    const meanAnomaly = ((t % period) / period) * 2 * Math.PI;

    const incRad = (INCLINATION_DEG * Math.PI) / 180;
    const latRad = Math.asin(Math.sin(incRad) * Math.sin(meanAnomaly));
    const latitude = (latRad * 180) / Math.PI;

    const lonAnomaly = Math.atan2(
      Math.sin(incRad) * Math.sin(meanAnomaly),
      Math.cos(incRad)
    );
    const earthRotation = EARTH_ROTATION_DEG_PER_S * t;
    let longitude = ((lonAnomaly * 180) / Math.PI - earthRotation) % 360;
    if (longitude > 180) longitude -= 360;
    if (longitude < -180) longitude += 360;

    this.state.spacecraft.latitude = latitude;
    this.state.spacecraft.longitude = longitude;
    this.state.spacecraft.headingDeg = ((meanAnomaly * 180) / Math.PI + 90) % 360;

    const orbitsCompleted = Math.floor(t / period);
    if (orbitsCompleted > this.state.spacecraft.orbitNumber - 1) {
      this.state.spacecraft.orbitNumber = orbitsCompleted + 1;
      this.addEvent("ORBIT", "INFO", `Orbit ${orbitsCompleted + 1} completed`);
    }
  }

  private updateAttitude(): void {
    const t = this.state.missionElapsed;
    const jitter = (seed: number, amplitude: number) =>
      Math.sin(t * 0.1 + seed) * amplitude + (seededRandom(this.tickCount + seed) - 0.5) * amplitude * 0.3;

    this.state.attitude.rollDeg = parseFloat((0.21 + jitter(1, 0.05)).toFixed(2));
    this.state.attitude.pitchDeg = parseFloat((-0.08 + jitter(2, 0.04)).toFixed(2));
    this.state.attitude.yawDeg = parseFloat(((t * 0.1) % 360).toFixed(2));
    this.state.attitude.pointingErrorDeg = parseFloat(
      Math.sqrt(
        this.state.attitude.rollDeg ** 2 + this.state.attitude.pitchDeg ** 2
      ).toFixed(2)
    );
  }

  private updatePower(elapsed: number): void {
    const t = this.state.missionElapsed;
    const period = ORBIT_PERIOD_S;
    const orbitPhase = (t % period) / period;
    const eclipseFraction = 0.35;
    const inEclipse = orbitPhase > (1 - eclipseFraction) / 2 && orbitPhase < (1 + eclipseFraction) / 2;

    this.state.power.eclipse = inEclipse;

    const solarAngle = inEclipse ? 0 : Math.cos((orbitPhase - 0.25) * 2 * Math.PI);
    const solarGen = inEclipse ? 0 : clamp(BASE_SOLAR_W * Math.max(0, solarAngle), 0, BASE_SOLAR_W);

    let consumption = BASE_CONSUMPTION_W;
    if (this.state.ai.status === "ONLINE") consumption += 0.3;
    if (this.state.power.eclipse) consumption += 0.1;

    this.state.power.solarGenerationW = parseFloat(solarGen.toFixed(2));
    this.state.power.powerConsumptionW = parseFloat(consumption.toFixed(2));
    this.state.power.powerBalanceW = parseFloat((solarGen - consumption).toFixed(2));

    const deltaWh = (solarGen - consumption) * (elapsed / 3600);
    this.state.power.batterySoc = clamp(
      this.state.power.batterySoc + (deltaWh / BATTERY_CAPACITY_WH) * 100,
      0,
      MAX_BATTERY_SOC
    );
    this.state.power.batterySoc = parseFloat(this.state.power.batterySoc.toFixed(1));
    this.state.power.batteryVoltage = parseFloat(
      (3.7 + (this.state.power.batterySoc / 100) * 4.3).toFixed(2)
    );

    if (this.state.faults.lowBattery) {
      this.state.power.batterySoc = clamp(this.state.power.batterySoc - 0.5, 5, 20);
      this.state.power.batterySoc = parseFloat(this.state.power.batterySoc.toFixed(1));
    }

    if (solarGen > consumption) {
      this.state.power.chargeState = "CHARGING";
    } else if (inEclipse) {
      this.state.power.chargeState = "DISCHARGING";
    } else {
      this.state.power.chargeState = "NOMINAL";
    }
  }

  private updateThermal(elapsed: number): void {
    const t = this.state.missionElapsed;
    const baseOBC = this.state.faults.thermalWarning ? 58 : 34.2;
    const thermalJitter = (seed: number) => Math.sin(t * 0.05 + seed) * 1.5;

    this.state.thermal.obc = parseFloat((baseOBC + thermalJitter(1)).toFixed(1));
    this.state.thermal.camera = parseFloat((30.8 + thermalJitter(2)).toFixed(1));
    this.state.thermal.battery = parseFloat((28.1 + thermalJitter(3) * 0.8).toFixed(1));
    this.state.thermal.comms = parseFloat((32.4 + thermalJitter(4)).toFixed(1));
    this.state.thermal.structure = parseFloat((24.7 + thermalJitter(5) * 0.5).toFixed(1));
  }

  private updateHealth(): void {
    if (this.state.faults.commLoss) {
      this.state.health.comms = "OFFLINE";
      this.state.health.ai = "OFFLINE";
    } else {
      this.state.health.comms = "LINKED";
      this.state.health.ai = "READY";
    }
    if (this.state.faults.lowBattery) {
      this.state.health.eps = "WARNING";
    } else {
      this.state.health.eps = "NOMINAL";
    }
    if (this.state.faults.thermalWarning) {
      this.state.health.thermal = "WARNING";
    } else {
      this.state.health.thermal = "NOMINAL";
    }
  }

  private updateGroundStations(): void {
    if (this.tickCount - this.lastStationCheckTick < 5) return;
    this.lastStationCheckTick = this.tickCount;

    const scLat = this.state.spacecraft.latitude;
    const scLon = this.state.spacecraft.longitude;

    let anyLinked = false;

    this.state.groundStations.forEach((gs) => {
      const dlat = (gs.latitude - scLat) * (Math.PI / 180);
      const dlon = (gs.longitude - scLon) * (Math.PI / 180);
      const a =
        Math.sin(dlat / 2) ** 2 +
        Math.cos((scLat * Math.PI) / 180) *
          Math.cos((gs.latitude * Math.PI) / 180) *
          Math.sin(dlon / 2) ** 2;
      const distKm = 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

      const maxRange = 2800;
      const isVisible = distKm < maxRange;
      const elevation = isVisible ? Math.max(0, 90 - (distKm / maxRange) * 90) : 0;

      gs.isVisible = isVisible;
      gs.elevationDeg = parseFloat(elevation.toFixed(1));

      if (isVisible && !this.state.faults.commLoss) {
        gs.isLinked = true;
        gs.status = "LINKED";
        anyLinked = true;
      } else {
        gs.isLinked = false;
        gs.status = isVisible ? "VISIBLE" : "STANDBY";
      }

      gs.nextPassSeconds = isVisible ? 0 : Math.max(60, Math.floor(seededRandom(this.tickCount + gs.latitude) * 4800));
    });

    if (!anyLinked && !this.state.faults.commLoss) {
      this.state.health.comms = "STANDBY";
    }
  }

  private processDownlink(elapsed: number): void {
    const items = this.state.downlink.items;
    const activeItems = items.filter((i) => i.status === "transmitting");

    if (activeItems.length > 0) {
      const linkedStation = this.state.groundStations.find((gs) => gs.isLinked);
      if (!linkedStation || this.state.faults.commLoss) {
        activeItems.forEach((item) => {
          item.status = "paused";
        });
        this.state.downlink.effectiveRateBytesS = 0;
        return;
      }

      const rate = 102400;
      activeItems.forEach((item) => {
        const transferBytes = rate * (elapsed / 1);
        item.bytesTransmitted = Math.min(item.bytesTransmitted + transferBytes, item.sizeBytes);
        item.progressPct = parseFloat(((item.bytesTransmitted / item.sizeBytes) * 100).toFixed(1));
        if (item.bytesTransmitted >= item.sizeBytes) {
          item.status = "complete";
          this.state.downlink.totalTransmitted++;
        }
      });

      this.state.downlink.effectiveRateBytesS = rate;
    } else {
      this.state.downlink.effectiveRateBytesS = 0;
    }

    const queued = items.filter((i) => i.status === "queued");
    if (queued.length > 0 && activeItems.length === 0) {
      const linkedStation = this.state.groundStations.find((gs) => gs.isLinked);
      if (linkedStation && !this.state.faults.commLoss) {
        const next = queued[0];
        next.status = "transmitting";
        next.assignedStation = linkedStation.name;
        this.addEvent("DOWNLINK", "INFO", `Downlink started: ${next.observationId} via ${linkedStation.name}`);
      }
    }

    this.state.downlink.items = items.filter((i) => i.status !== "complete");
    this.state.downlink.queueSize = this.state.downlink.items.length;

    const totalActiveBytes = activeItems.reduce((sum, i) => sum + i.sizeBytes - i.bytesTransmitted, 0);
    const totalTransferred = activeItems.reduce((sum, i) => sum + i.bytesTransmitted, 0);
    this.state.downlink.progress = {
      queuedCount: queued.length,
      activeCount: activeItems.filter((i) => i.status === "transmitting").length,
      completedCount: this.state.downlink.totalTransmitted,
      overallProgressPct:
        totalActiveBytes + totalTransferred > 0
          ? parseFloat(((totalTransferred / (totalActiveBytes + totalTransferred)) * 100).toFixed(1))
          : 0,
    };
    this.state.downlink.totalBytes = this.state.downlink.totalTransmitted * 2048000;
  }

  private updateHotspots(): void {
    if (this.tickCount % 10 !== 0) return;

    const scenario = this.state.scenario;
    const scLat = this.state.spacecraft.latitude;
    const scLon = this.state.spacecraft.longitude;

    if (scenario === "WILDFIRE" || scenario === "HIGH PRIORITY") {
      const clusterLat = scLat + (seededRandom(this.tickCount) - 0.5) * 10;
      const clusterLon = scLon + (seededRandom(this.tickCount + 1) - 0.5) * 10;
      const count = scenario === "HIGH PRIORITY" ? 5 : 3;
      this.state.hotspots = [];
      for (let i = 0; i < count; i++) {
        this.state.hotspots.push({
          id: `FIRE-${String(i + 1).padStart(3, "0")}`,
          lat: clusterLat + (seededRandom(this.tickCount + i * 2) - 0.5) * 4,
          lon: clusterLon + (seededRandom(this.tickCount + i * 2 + 1) - 0.5) * 4,
          frp: parseFloat((30 + seededRandom(this.tickCount + i * 3) * 120).toFixed(1)),
          confidence: seededRandom(this.tickCount + i * 4) > 0.5 ? "high" : "nominal",
        });
      }
    } else {
      this.state.hotspots = [
        { id: "FIRE-001", lat: 37.75 + (seededRandom(this.tickCount) - 0.5) * 2, lon: -122.42 + (seededRandom(this.tickCount + 5) - 0.5) * 2, frp: parseFloat((10 + seededRandom(this.tickCount + 6) * 40).toFixed(1)), confidence: "low" },
      ];
    }
  }

  private checkObservations(): void {
    const interval = this.scenarioConfig.observationInterval;
    const speed = this.state.simSpeed;
    const effectiveInterval = Math.max(5, Math.floor(interval / speed));

    if (this.tickCount - this.lastObservationTick < effectiveInterval) return;
    this.lastObservationTick = this.tickCount;

    if (this.state.health.camera !== "ACTIVE" && this.state.health.camera !== "NOMINAL") return;

    const [minScore, maxScore] = this.scenarioConfig.smokeScoreRange;
    const seed = this.tickCount * 7.31;
    const smokeScore = parseFloat((minScore + seededRandom(seed) * (maxScore - minScore)).toFixed(3));

    let confidence = "HIGH";
    if (smokeScore > 0.85) confidence = "VERY HIGH";
    else if (smokeScore > 0.6) confidence = "HIGH";
    else if (smokeScore > 0.3) confidence = "MEDIUM";
    else confidence = "LOW";

    let priority = "LOW";
    if (smokeScore > 0.8) priority = "CRITICAL";
    else if (smokeScore > 0.6) priority = "HIGH";
    else if (smokeScore > 0.35) priority = "MEDIUM";

    const evidenceCount = Math.floor(seededRandom(seed + 1) * 3) + 1;
    const altCount = Math.floor(seededRandom(seed + 2) * 2);
    const visualEvidence: string[] = [];
    const alternativeExplanations: string[] = [];
    for (let i = 0; i < evidenceCount; i++) {
      const idx = Math.floor(seededRandom(seed + i + 10) * VISUAL_EVIDENCE_POOL.length);
      if (!visualEvidence.includes(VISUAL_EVIDENCE_POOL[idx])) {
        visualEvidence.push(VISUAL_EVIDENCE_POOL[idx]);
      }
    }
    for (let i = 0; i < altCount; i++) {
      const idx = Math.floor(seededRandom(seed + i + 20) * ALTERNATIVE_EXPLANATIONS.length);
      if (!alternativeExplanations.includes(ALTERNATIVE_EXPLANATIONS[idx])) {
        alternativeExplanations.push(ALTERNATIVE_EXPLANATIONS[idx]);
      }
    }

    const obsId = `OBS-${String(this.state.observations.length + 1).padStart(4, "0")}`;
    const h = Math.floor(this.state.missionElapsed / 3600) % 24;
    const m = Math.floor((this.state.missionElapsed % 3600) / 60);
    const s = Math.floor(this.state.missionElapsed % 60);
    const timestamp = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")} UTC`;

    const observation: DemoObservation = {
      id: obsId,
      timestamp,
      latitude: this.state.spacecraft.latitude,
      longitude: this.state.spacecraft.longitude,
      altitudeKm: this.state.spacecraft.altitudeKm,
      cameraAngle: 15,
      smokeScore,
      confidence,
      priority,
      status: "CAPTURED",
      visualEvidence,
      alternativeExplanations,
      sentinelAvailable: false,
      sentinelSceneId: null,
      sentinelAcquisitionTime: null,
      sentinelCloudCover: null,
      sentinelProduct: null,
      sentinelTrueColorUrl: null,
      sentinelNdviUrl: null,
      sentinelFalseColorUrl: null,
    };

    this.state.observations.unshift(observation);
    if (this.state.observations.length > 50) {
      this.state.observations.pop();
    }

    this.state.ai.latestObservationId = obsId;
    this.state.ai.smokeScore = smokeScore;
    this.state.ai.confidence = confidence;
    this.state.ai.latencyMs = parseFloat((1.2 + seededRandom(seed + 5) * 2.0).toFixed(2));
    this.state.ai.visualEvidence = visualEvidence;
    this.state.ai.alternativeExplanations = alternativeExplanations;

    this.addEvent("OBSERVATION", "INFO", `Observation captured: ${obsId}`);
    this.addEvent("AI ANALYSIS", "INFO", `Smoke score: ${smokeScore.toFixed(3)} (${confidence})`);

    if (smokeScore > 0.6) {
      this.addEvent("PRIORITY", "WARNING", `High priority detection: ${obsId} score=${smokeScore.toFixed(3)}`);
    }

    const sizeBytes = Math.floor(1024 * 1024 * (1.5 + seededRandom(seed + 6) * 2.5));
    const downlinkItem: DemoDownlinkItem = {
      observationId: obsId,
      priority,
      sizeBytes,
      status: "queued",
      bytesTransmitted: 0,
      progressPct: 0,
      assignedStation: null,
      band: "X-BAND",
      rateBytesS: 0,
    };
    this.state.downlink.items.push(downlinkItem);
    this.state.downlink.queueSize = this.state.downlink.items.length;
  }

  private addEvent(type: string, severity: string, message: string): void {
    const h = Math.floor(this.state.missionElapsed / 3600) % 24;
    const m = Math.floor((this.state.missionElapsed % 3600) / 60);
    const s = Math.floor(this.state.missionElapsed % 60);
    const timestamp = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")} UTC`;

    this.eventCounter++;
    this.state.events.unshift({
      id: `EVT-${String(this.eventCounter).padStart(6, "0")}`,
      timestamp,
      type,
      severity,
      message,
    });
  }

  private pruneEvents(): void {
    if (this.state.events.length > 100) {
      this.state.events = this.state.events.slice(0, 100);
    }
  }
}
