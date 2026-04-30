import { Router, type IRouter } from "express";
import healthRouter from "./health";
import sportsRouter from "./sports";
import oddsRouter from "./odds";
import opportunitiesRouter from "./opportunities";
import alertsRouter from "./alerts";
import configRouter from "./config";

const router: IRouter = Router();

router.use(healthRouter);
router.use(configRouter);
router.use(sportsRouter);
router.use(oddsRouter);
router.use(opportunitiesRouter);
router.use(alertsRouter);

export default router;
