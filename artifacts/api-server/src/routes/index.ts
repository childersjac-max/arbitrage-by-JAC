import { Router, type IRouter } from "express";
import healthRouter from "./health";
import lineTrackerRouter from "./line-tracker";
import nbaModelRouter from "./nba-model";
import arbitrageRouter from "./arbitrage";

const router: IRouter = Router();

router.use(healthRouter);
router.use(lineTrackerRouter);
router.use(nbaModelRouter);
router.use(arbitrageRouter);

export default router;
