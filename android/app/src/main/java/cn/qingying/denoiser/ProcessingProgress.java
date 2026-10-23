package cn.qingying.denoiser;

/** Thread-safe, monotonic-clock progress shared by the worker and UI ticker. */
final class ProcessingProgress {
  private final long started;
  private long sampleStarted;
  private int before, expected, total, completed, pass, passes;
  private String stage = "准备处理", device = "";
  private boolean measurable;

  ProcessingProgress(long now) { started = now; }

  static int tiles(int width, int height, int engine) {
    int count = ((width + 127) / 128) * ((height + 127) / 128);
    return count * (engine == 1 && Math.max(width, height) > 128 ? 5 : 1);
  }

  synchronized void beginPass(int before, int expected, int total, int pass, int passes) {
    this.before = before;
    this.expected = expected;
    this.total = total;
    this.completed = before;
    this.pass = pass;
    this.passes = passes;
    stage = "加载模型";
    measurable = false;
  }

  synchronized void update(int done, int count, String backend, long now) {
    device = backend;
    if (count <= 0) {
      // A GPU retry discards partial work for this pass. Do not retain its ETA.
      completed = before;
      stage = "加载模型";
      measurable = false;
      return;
    }
    if (count != expected || done < 0 || done > count)
      throw new IllegalArgumentException("Invalid inference progress");
    if (!measurable || done == 0) sampleStarted = now;
    completed = before + done;
    stage = "AI 推理";
    measurable = true;
  }

  synchronized void stage(String name) {
    stage = name;
    measurable = false;
  }

  synchronized String device() { return device; }

  synchronized Snapshot snapshot(long now) {
    long elapsed = Math.max(0, now - started);
    long sample = Math.max(0, now - sampleStarted);
    int done = completed - before;
    // Wait for two completed units and two seconds before estimating throughput.
    double rate = measurable && done >= 2 && sample >= 2000 ? done * 1000.0 / sample : 0;
    long remaining = rate > 0 ? (long) Math.ceil((total - completed) / rate) : -1;
    return new Snapshot(stage, device, measurable, completed, total, pass, passes,
        elapsed, rate, remaining);
  }

  static final class Snapshot {
    final String stage, device;
    final boolean measurable;
    final int completed, total, pass, passes;
    final long elapsed, remaining;
    final double rate;

    Snapshot(String stage, String device, boolean measurable, int completed, int total,
        int pass, int passes, long elapsed, double rate, long remaining) {
      this.stage = stage; this.device = device; this.measurable = measurable;
      this.completed = completed; this.total = total; this.pass = pass; this.passes = passes;
      this.elapsed = elapsed; this.rate = rate; this.remaining = remaining;
    }

    int percent() { return total > 0 ? (int) (100L * completed / total) : 0; }
  }
}
