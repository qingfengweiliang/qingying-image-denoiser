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
      activity.nativeProcess(fixture, out, activity.getFilesDir().getPath(), engine, 3, factor);
      assertEquals(128, Color.alpha(out.getPixel(16, 16)), 2);
      assertTrue(Color.red(out.getPixel(16, 16)) > 20);
      out.recycle();
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
