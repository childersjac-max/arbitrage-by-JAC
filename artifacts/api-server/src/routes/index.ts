import { Router, type IRouter } from "express";
import healthRouter from "./health";
import configRouter from "./config";
import diagnosticsRouter from "./diagnostics";
import sportsRouter from "./sports";
import oddsRouter from "./odds";
import trackedGamesRouter from "./tracked-games";
import opportunitiesRouter from "./opportunities";
import historyRouter from "./history";
import alertsRouter from "./alerts";
import monitorRouter from "./monitor";

const router: IRouter = Router();

router.use(healthRouter);
router.use(configRouter);
router.use(diagnosticsRouter);
router.use(sportsRouter);
router.use(oddsRouter);
router.use(trackedGamesRouter);
router.use(opportunitiesRouter);
router.use(historyRouter);
router.use(alertsRouter);
router.use(monitorRouter);

export default router;
