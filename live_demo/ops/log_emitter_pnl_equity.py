    def emit_pnl_equity(
        self,
        *,
        ts: Optional[float],
        symbol: str,
        equity_value: float,
        pnl_total_usd: float,
        realized_pnl_usd: Optional[float] = None,
        unrealized_pnl_usd: Optional[float] = None,
        realized_return_bps: Optional[float] = None,
        position_qty: Optional[float] = None,
        position_avg_px: Optional[float] = None,
        current_price: Optional[float] = None,
        starting_equity: Optional[float] = None,
        peak_equity: Optional[float] = None,
        drawdown_pct: Optional[float] = None,
    ):
        """Emit PnL and equity log with flattened structure."""
        # Calculate derived fields if not provided
        drawdown_usd = None
        return_pct = None
        return_usd = None
        
        if peak_equity is not None and equity_value is not None:
            drawdown_usd = peak_equity - equity_value
            if drawdown_pct is None and peak_equity > 0:
                drawdown_pct = 100.0 * (peak_equity - equity_value) / peak_equity
        
        if starting_equity is not None and equity_value is not None and starting_equity > 0:
            return_usd = equity_value - starting_equity
            return_pct = 100.0 * (equity_value - starting_equity) / starting_equity
        
        payload = {
            "symbol": symbol,
            
            # Required fields
            "equity_value": equity_value,
            "pnl_total_usd": pnl_total_usd,
            
            # PnL breakdown
            "realized_pnl_usd": realized_pnl_usd,
            "unrealized_pnl_usd": unrealized_pnl_usd,
            "realized_return_bps": realized_return_bps,
            
            # Position info
            "position_qty": position_qty,
            "position_avg_px": position_avg_px,
            "current_price": current_price,
            
            # Equity tracking
            "starting_equity": starting_equity,
            "peak_equity": peak_equity,
            
            # Risk metrics
            "drawdown_pct": drawdown_pct,
            "drawdown_usd": drawdown_usd,
            "return_pct": return_pct,
            "return_usd": return_usd,
        }
        self._write("pnl_equity", payload, ts=ts)
