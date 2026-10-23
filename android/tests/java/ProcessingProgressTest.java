package cn.qingying.denoiser;

public final class ProcessingProgressTest {
  static void check(boolean value, String message) {
    if (!value) throw new AssertionError(message);
  }

  public static void main(String[] args) {
    check(ProcessingProgress.tiles(128, 128, 0) == 1, "one tile");
    check(ProcessingProgress.tiles(129, 3, 0) == 2, "partial tiles");
    check(ProcessingProgress.tiles(129, 3, 1) == 10, "all five CUGAN sweeps");
    check(ProcessingProgress.tiles(1, 1, 1) == 1, "CUGAN without SE sweeps");

    ProcessingProgress tracker = new ProcessingProgress(1000);
    tracker.beginPass(0, 10, 10, 1, 1);
    tracker.update(0, 10, "GPU", 2000);
    tracker.update(1, 10, "GPU", 3000);
    check(tracker.snapshot(3000).rate == 0, "no unreliable early ETA");
    tracker.update(4, 10, "GPU", 6000);
    ProcessingProgress.Snapshot halfway = tracker.snapshot(6000);
    check(halfway.percent() == 40, "measured percentage");
    check(halfway.rate == 1.0 && halfway.remaining == 6, "measured speed and ETA");
    check(halfway.elapsed == 5000, "elapsed includes preparation");
    check(tracker.snapshot(8000).remaining == 9, "ETA adjusts during slow tiles");

    tracker.update(0, 0, "CPU fallback", 8000);
    check(!tracker.snapshot(8000).measurable, "retry shows loading stage");
    tracker.update(0, 10, "CPU", 9000);
    check(tracker.snapshot(9000).percent() == 0, "discard failed GPU work");
    tracker.update(2, 10, "CPU", 13000);
    check(tracker.snapshot(13000).rate == .5, "CPU speed excludes failed GPU attempt");
    check(tracker.snapshot(13000).elapsed == 12000, "total time includes retry");
    tracker.update(10, 10, "CPU", 29000);
    check(tracker.snapshot(29000).percent() == 100, "inference complete");
    tracker.stage("编码结果");
    check(!tracker.snapshot(30000).measurable, "encoding never pretends inference is still running");

    int first = ProcessingProgress.tiles(129, 129, 0);
    int second = ProcessingProgress.tiles(258, 258, 0);
    tracker = new ProcessingProgress(0);
    tracker.beginPass(0, first, first + second, 1, 2);
    tracker.update(first, first, "CPU", 10000);
    check(tracker.snapshot(10000).percent() == 30, "4x passes weighted by actual tile counts");
    tracker.beginPass(first, second, first + second, 2, 2);
    tracker.update(0, second, "CPU", 11000);
    check(tracker.snapshot(11000).percent() == 30, "no 4x progress reset");
    tracker.update(second, second, "CPU", 30000);
    check(tracker.snapshot(30000).percent() == 100, "both 4x passes complete");

    boolean rejected = false;
    try { tracker.update(99, 1, "CPU", 31000); }
    catch (IllegalArgumentException expected) { rejected = true; }
    check(rejected, "reject mismatched native callback totals");
    System.out.println("PASS measured progress, ETA, retries, SE sweeps and 4x weighting");
  }
}
