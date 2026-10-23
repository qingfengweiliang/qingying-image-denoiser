package cn.qingying.denoiser;

import static org.junit.Assert.*;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.net.Uri;
import androidx.test.platform.app.InstrumentationRegistry;
import java.io.*;
import org.junit.Test;

public class AndroidSmokeTest {
  @Test
  public void importProcessCompareExport() throws Exception {
    Instrumentation inst = InstrumentationRegistry.getInstrumentation();
    Intent launch =
        inst.getTargetContext()
            .getPackageManager()
            .getLaunchIntentForPackage("cn.qingying.denoiser");
    MainActivity activity = (MainActivity) inst.startActivitySync(launch);
    awaitIdle(inst, activity);
    assertNotNull(activity.processor);
    File input = new File(activity.getCacheDir(), "test-input.png");
    Bitmap fixture = Bitmap.createBitmap(33, 35, Bitmap.Config.ARGB_8888);
    for (int y = 0; y < 35; y++)
      for (int x = 0; x < 33; x++)
        fixture.setPixel(x, y, Color.argb(128, 96 + (x % 3) * 8, 144, 192));
    try (OutputStream out = new FileOutputStream(input)) {
      fixture.compress(Bitmap.CompressFormat.PNG, 100, out);
    }
    inst.runOnMainSync(
        () ->
            activity.onActivityResult(
                1, Activity.RESULT_OK, new Intent().setData(Uri.fromFile(input))));
    awaitIdle(inst, activity);
    assertNotNull(activity.original);
    assertEquals(33, activity.original.getWidth());
    for (int mode = 0; mode < 6; mode++) {
      final int selected = mode;
      inst.runOnMainSync(() -> activity.algorithm.setSelection(selected));
      inst.waitForIdleSync();
      inst.runOnMainSync(
          () -> {
            activity.result = null;
            activity.process();
          });
      awaitIdle(inst, activity);
      assertNotNull("mode=" + mode, activity.result);
      assertEquals(33, activity.result.getWidth());
      assertEquals(35, activity.result.getHeight());
      assertEquals(128, Color.alpha(activity.result.getPixel(16, 16)), 2);
      assertTrue(activity.save.isEnabled());
      System.out.println("PASS Android algorithm=" + mode);
    }
    for (String fmt : new String[] {"PNG", "JPEG", "WEBP"}) {
      File output = new File(activity.getCacheDir(), "test-export");
      activity.processor.callAttr("export", activity.resultFile.getPath(), output.getPath(), fmt);
      assertTrue(output.length() > 0);
      Bitmap decoded = android.graphics.BitmapFactory.decodeFile(output.getPath());
      assertNotNull(decoded);
      assertEquals(33, decoded.getWidth());
      assertEquals(35, decoded.getHeight());
      decoded.recycle();
      if (fmt.equals("WEBP")) {
        File roundTrip = new File(activity.getCacheDir(), "webp-import.png");
        activity.processor.callAttr("prepare", output.getPath(), roundTrip.getPath());
        Bitmap imported = android.graphics.BitmapFactory.decodeFile(roundTrip.getPath());
        assertNotNull(imported);
        assertEquals(33, imported.getWidth());
        imported.recycle();
      }
      System.out.println("PASS Android export=" + fmt);
    }
    for (int engine = 0; engine < 2; engine++) {
      int factor = engine == 0 ? 2 : 3;
      Bitmap out = Bitmap.createBitmap(33 * factor, 35 * factor, Bitmap.Config.ARGB_8888);
      activity.nativeProcess(fixture, out, activity.getFilesDir().getPath(), engine, 3, factor,
          1, null);
      assertEquals(128, Color.alpha(out.getPixel(16, 16)), 2);
      assertTrue(Color.red(out.getPixel(16, 16)) > 20);
      out.recycle();
    }
    inst.runOnMainSync(activity::finish);
  }

  @Test
  public void cpuAndAutoReportCompletedTiles() throws Exception {
    Instrumentation inst = InstrumentationRegistry.getInstrumentation();
    MainActivity activity = (MainActivity) inst.startActivitySync(
        inst.getTargetContext().getPackageManager().getLaunchIntentForPackage("cn.qingying.denoiser"));
    awaitIdle(inst, activity);
    Bitmap source = Bitmap.createBitmap(129, 3, Bitmap.Config.ARGB_8888);
    source.eraseColor(Color.argb(128, 96, 144, 192));
    try {
      for (int engine = 0; engine < 2; engine++) {
        for (int backend = 0; backend < 2; backend++) {
          int factor = engine == 0 ? 1 : 2;
          Bitmap output = Bitmap.createBitmap(129 * factor, 3 * factor, Bitmap.Config.ARGB_8888);
          final int[] last = {0, 0};
          final boolean[] inference = {false};
          String device = activity.nativeProcess(source, output, activity.getFilesDir().getPath(),
              engine, 2, factor, backend, (done, count, name) -> {
                if (count == 0) { last[0] = 0; return; } // Includes GPU retry.
                assertTrue(done >= last[0]);
                assertTrue(done <= count);
                last[0] = done;
                last[1] = count;
                inference[0] = true;
              });
          assertTrue(inference[0]);
          assertEquals(engine == 0 ? 2 : 10, last[1]);
          assertEquals(last[1], last[0]);
          assertTrue(device.startsWith(backend == 1 ? "CPU" : "GPU") || device.startsWith("CPU"));
          assertEquals(128, Color.alpha(output.getPixel(0, 0)), 2);
          assertTrue(Color.red(output.getPixel(0, 0)) > 20);
          output.recycle();
        }
      }
    } finally {
      source.recycle();
      inst.runOnMainSync(activity::finish);
    }
  }

  @Test
  public void uiShowsTwoPassProgressAndCompletion() throws Exception {
    Instrumentation inst = InstrumentationRegistry.getInstrumentation();
    MainActivity activity = (MainActivity) inst.startActivitySync(
        inst.getTargetContext().getPackageManager().getLaunchIntentForPackage("cn.qingying.denoiser"));
    awaitIdle(inst, activity);
    Bitmap fixture = Bitmap.createBitmap(129, 65, Bitmap.Config.ARGB_8888);
    fixture.eraseColor(Color.argb(160, 96, 144, 192));
    File input = new File(activity.getCacheDir(), "ui-progress-input.png");
    try (OutputStream stream = new FileOutputStream(input)) {
      fixture.compress(Bitmap.CompressFormat.PNG, 100, stream);
    }
    fixture.recycle();
    inst.runOnMainSync(() -> activity.onActivityResult(
        1, Activity.RESULT_OK, new Intent().setData(Uri.fromFile(input))));
    awaitIdle(inst, activity);
    inst.runOnMainSync(() -> activity.algorithm.setSelection(0));
    inst.waitForIdleSync();
    inst.runOnMainSync(() -> {
      activity.backend.setSelection(1);
      activity.scale.setSelection(2); // Waifu2x 4x, two passes.
    });
    inst.waitForIdleSync();
    inst.runOnMainSync(activity::process);
    final boolean[] running = {true};
    long deadline = System.currentTimeMillis() + 180000;
    boolean captured = false;
    while (System.currentTimeMillis() < deadline) {
      final boolean[] visibleProgress = {false};
      inst.runOnMainSync(() -> {
        running[0] = activity.busy;
        if (activity.processingProgress != null) {
          ProcessingProgress.Snapshot s = activity.processingProgress.snapshot(android.os.SystemClock.elapsedRealtime());
          assertTrue(s.completed >= 0 && s.completed <= s.total);
          visibleProgress[0] = s.measurable && s.completed > 0 && s.completed < s.total;
        }
      });
      if (visibleProgress[0] && !captured) {
        screenshot(inst, activity, "progress.png");
        captured = true;
      }
      if (!running[0]) break;
      Thread.sleep(100);
    }
    assertFalse("UI processing timed out", running[0]);
    assertNotNull(activity.result);
    assertEquals(516, activity.result.getWidth());
    assertEquals(260, activity.result.getHeight());
    assertEquals(160, Color.alpha(activity.result.getPixel(100, 100)), 2);
    inst.runOnMainSync(() -> {
      assertTrue(activity.status.getText().toString().contains("处理完成"));
      assertTrue(activity.status.getText().toString().contains("MP/秒"));
      assertTrue(activity.backend.isEnabled());
      assertTrue(activity.save.isEnabled());
    });
    screenshot(inst, activity, "completed.png");
    inst.runOnMainSync(activity::finish);
  }

  void screenshot(Instrumentation inst, MainActivity activity, String name) throws IOException {
    Bitmap screen = inst.getUiAutomation().takeScreenshot();
    if (screen == null) return;
    File directory = new File(activity.getExternalFilesDir(null), "qa");
    directory.mkdirs();
    try (OutputStream stream = new FileOutputStream(new File(directory, name))) {
      screen.compress(Bitmap.CompressFormat.PNG, 100, stream);
    } finally {
      screen.recycle();
    }
  }

  void awaitIdle(Instrumentation inst, MainActivity activity) throws Exception {
    long deadline = System.currentTimeMillis() + 180000;
    final boolean[] busy = {true};
    do {
      inst.waitForIdleSync();
      inst.runOnMainSync(() -> busy[0] = activity.busy);
      if (!busy[0]) return;
      Thread.sleep(200);
    } while (System.currentTimeMillis() < deadline);
    fail("Timed out waiting for local processing");
  }
}
