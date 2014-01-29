package eu.deustotech.internet.linkedtagworld.lib;

import java.io.IOException;
import java.net.MalformedURLException;
import java.net.URL;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.AsyncTask;

public class RetrieveHTTPBitmap extends AsyncTask<String, Void, Bitmap>{

	@Override
	protected Bitmap doInBackground(String... params) {
		String object = params[0];
		Bitmap bm = null;
		try {
			bm = BitmapFactory.decodeStream(new URL(object).openConnection().getInputStream());
		} catch (MalformedURLException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return bm;
	}

}
